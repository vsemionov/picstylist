import logging

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

import torchvision.transforms as transforms

from . import weights


NUM_STEPS = 320
LEARNING_RATE = 1.0
LBFGS_KWARGS = {'history_size': 10}
CONTENT_LAYERS = ['conv3_2']  # alternative: conv4_1 (or coarser: conv4_2)
STYLE_LAYERS = ['conv1_1', 'conv2_1', 'conv3_1', 'conv4_1', 'conv5_1']
MAX_STYLE_WEIGHT = 1_000_000
CONTENT_WEIGHT = 1
TV_WEIGHT = 5e-6
NOISE = 0.1, 0.45  # scaling reduces losses a tiny bit


logger = logging.getLogger(__name__)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
torch.set_default_device(device)

cnn = weights.get_vgg_model().features.eval().requires_grad_(False)
cnn_normalization_mean = torch.tensor([0.485, 0.456, 0.406])
cnn_normalization_std = torch.tensor([0.229, 0.224, 0.225])

to_tensor = transforms.ToTensor()
to_image = transforms.ToPILImage()
convert_image = lambda image: to_tensor(image).to(device)


def gram_matrix(input):
    a, b, c, d = input.size()
    features = input.view(b, c * d)
    G = features @ features.t()
    return G / (b * c * d)


class ContentLoss(nn.Module):
    def __init__(self, target):
        super().__init__()
        self.target = target

    def forward(self, input):
        if input.size() == self.target.size():
            self.loss = F.mse_loss(input, self.target)
        else:
            self.loss = torch.tensor(0)
        return input


class StyleLoss(nn.Module):
    def __init__(self, target_feature):
        super().__init__()
        self.target = gram_matrix(target_feature)

    def forward(self, input):
        G = gram_matrix(input)
        self.loss = F.mse_loss(G, self.target)
        return input


class TotalVariationLoss(nn.Module):
    def __call__(self, input):
        dx = input[:, :, :, 1:] - input[:, :, :, :-1]
        dy = input[:, :, 1:, :] - input[:, :, :-1, :]
        loss = torch.sum(torch.abs(dx)) + torch.sum(torch.abs(dy)) / (dx.numel() + dy.numel())
        return loss


class Normalization(nn.Module):
    def __init__(self, mean, std):
        super().__init__()
        self.mean = mean.view(-1, 1, 1)
        self.std = std.view(-1, 1, 1)

    def forward(self, img):
        return (img - self.mean) / self.std


def get_layers():
    block = 1
    conv = 0
    for layer in cnn.children():
        if isinstance(layer, nn.Conv2d):
            conv += 1
            name = f'conv{block}_{conv}'
        elif isinstance(layer, nn.BatchNorm2d):
            name = f'bn{block}_{conv}'
        elif isinstance(layer, nn.ReLU):
            name = f'relu{block}_{conv}'
            layer = nn.ReLU(inplace=False)
        elif isinstance(layer, nn.MaxPool2d):
            name = f'pool{block}'
            layer = nn.AvgPool2d(2)
            block += 1
            conv = 0
        else:
            raise RuntimeError(f'Unrecognized layer: {layer.__class__.__name__}')
        yield name, layer


def get_style_model_and_losses(content_image, style_image):
    normalization = Normalization(cnn_normalization_mean, cnn_normalization_std)
    model = nn.Sequential(normalization)

    content_losses = []
    style_losses = []

    c = 1
    s = 1
    for name, layer in get_layers():
        model.add_module(name, layer)

        if name in CONTENT_LAYERS:
            target = model(content_image)
            content_loss = ContentLoss(target)
            model.add_module(f'content_loss_{c}', content_loss)
            content_losses.append(content_loss)
            c += 1

        if name in STYLE_LAYERS:
            target_feature = model(style_image)
            style_loss = StyleLoss(target_feature)
            model.add_module(f'style_loss_{s}', style_loss)
            style_losses.append(style_loss)
            s += 1

    last = -1
    for i, layer in enumerate(model):
        if isinstance(layer, (ContentLoss, StyleLoss)):
            last = i
    model = model[:last + 1]

    return model, content_losses, style_losses


def run_style_transfer(content_image, style_image, content_weight, style_weight, tv_weight):
    model, content_losses, style_losses = get_style_model_and_losses(content_image, style_image)

    work_image = torch.rand(content_image.size()) * NOISE[0] + NOISE[1]
    work_image.requires_grad_(True)

    model.eval()

    optimizer = optim.LBFGS([work_image], lr=LEARNING_RATE, max_iter=NUM_STEPS, **LBFGS_KWARGS)
    tv_loss_fn = TotalVariationLoss()

    step = 0

    def get_loss_and_grad():
        nonlocal step

        with torch.no_grad():
            work_image.clamp_(0, 1)

        model(work_image)

        content_loss = torch.stack([cl.loss for cl in content_losses]).sum() * content_weight
        style_loss = torch.stack([sl.loss for sl in style_losses]).sum() * style_weight
        tv_loss = (tv_loss_fn(work_image) * tv_weight) if tv_weight else torch.tensor(0)
        loss = content_loss + style_loss + tv_loss

        optimizer.zero_grad()
        loss.backward()

        step += 1

        if step % 50 == 0 or step in (1, NUM_STEPS):
            logger.info('Step: %d/%d, content loss: %.2e, style loss: %.2e, tv loss: %.2e', step, NUM_STEPS,
                content_loss.item(), style_loss.item(), tv_loss.item())

        return loss

    optimizer.step(get_loss_and_grad)

    with torch.no_grad():
        work_image.clamp_(0, 1)

    return work_image.detach()


def style_transfer(content_image, style_image, strength):
    content_image = convert_image(content_image).unsqueeze(0)
    style_image = convert_image(style_image).unsqueeze(0)
    style_weight = MAX_STYLE_WEIGHT * strength / 100
    output = run_style_transfer(content_image, style_image, CONTENT_WEIGHT, style_weight, TV_WEIGHT)
    return to_image(output[0])


last = -1
for i, (name, _) in enumerate(get_layers()):
    if name in CONTENT_LAYERS or name in STYLE_LAYERS:
        last = i
cnn = cnn[:last + 1]
