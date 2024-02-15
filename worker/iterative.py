import logging

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

from torchvision import transforms
from torchvision.models import vgg19, VGG19_Weights

from PIL import Image


MAX_SIZE = 128
NUM_STEPS = 320

CONTENT_LAYERS = ['conv_5']
STYLE_LAYERS = ['conv_1', 'conv_2', 'conv_3', 'conv_4', 'conv_5']

MAX_STYLE_WEIGHT = 1e4
CONTENT_WEIGHT = 1e-2


logger = logging.getLogger(__name__)


device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
torch.set_default_device(device)

cnn = vgg19(weights=VGG19_Weights.DEFAULT).features.eval()

cnn_normalization_mean = torch.tensor([0.485, 0.456, 0.406])
cnn_normalization_std = torch.tensor([0.229, 0.224, 0.225])


def gram_matrix(input):
    a, b, c, d = input.size()
    features = input.view(a * b, c * d)
    G = torch.mm(features, features.t())
    return G.div(a * b * c * d)


class ContentLoss(nn.Module):
    def __init__(self, target):
        super().__init__()
        # we 'detach' the target content from the tree used
        # to dynamically compute the gradient: this is a stated value,
        # not a variable. Otherwise the forward method of the criterion
        # will throw an error.
        self.target = target.detach()

    def forward(self, input):
        self.loss = torch.tensor(0)
        if input.shape == self.target.shape:
            self.loss = F.mse_loss(input, self.target)
        return input


class StyleLoss(nn.Module):
    def __init__(self, target_feature):
        super(StyleLoss, self).__init__()
        self.target = gram_matrix(target_feature).detach()

    def forward(self, input):
        G = gram_matrix(input)
        self.loss = F.mse_loss(G, self.target)
        return input


class Normalization(nn.Module):
    def __init__(self, mean, std):
        super(Normalization, self).__init__()
        # .view the mean and std to make them [C x 1 x 1] so that they can
        # directly work with image Tensor of shape [B x C x H x W].
        # B is batch size. C is number of channels. H is height and W is width.
        self.mean = mean.view(-1, 1, 1)
        self.std = std.view(-1, 1, 1)

    def forward(self, img):
        return (img - self.mean) / self.std


def get_style_model_and_losses(content_image, style_image):
    normalization = Normalization(cnn_normalization_mean, cnn_normalization_std)

    content_losses = []
    style_losses = []

    model = nn.Sequential(normalization)

    i = 0
    for layer in cnn.children():
        if isinstance(layer, nn.Conv2d):
            i += 1
            name = f'conv_{i}'
        elif isinstance(layer, nn.ReLU):
            name = f'relu_{i}'
            # The in-place version doesn't play very nicely with the ``ContentLoss``
            # and ``StyleLoss`` we insert below. So we replace with out-of-place
            # ones here.
            layer = nn.ReLU(inplace=False)
        elif isinstance(layer, nn.MaxPool2d):
            name = f'pool_{i}'
        elif isinstance(layer, nn.BatchNorm2d):
            name = f'bn_{i}'
        else:
            raise RuntimeError(f'Unrecognized layer: {layer.__class__.__name__}')

        model.add_module(name, layer)

        if name in CONTENT_LAYERS:
            target = model(content_image).detach()
            content_loss = ContentLoss(target)
            model.add_module(f'content_loss_{i}', content_loss)
            content_losses.append(content_loss)

        if name in STYLE_LAYERS:
            target_feature = model(style_image).detach()
            style_loss = StyleLoss(target_feature)
            model.add_module(f'style_loss_{i}', style_loss)
            style_losses.append(style_loss)

    for i in range(len(model) - 1, -1, -1):
        if isinstance(model[i], ContentLoss) or isinstance(model[i], StyleLoss):
            break

    model = model[:(i + 1)]

    return model, content_losses, style_losses


def run_style_transfer(content_image, style_image, content_weight, style_weight):
    # TODO: tune optimizer
    model, content_losses, style_losses = get_style_model_and_losses(content_image, style_image)

    work_image = content_image.clone()  # TODO: avoid cloning
    work_image.requires_grad_(True)

    model.eval()
    model.requires_grad_(False)

    optimizer = optim.LBFGS([work_image], max_iter=1)

    step = 0
    while step < NUM_STEPS:
        def closure():
            nonlocal step

            with torch.no_grad():
                work_image.clamp_(0, 1)

            optimizer.zero_grad()
            model(work_image)
            content_loss = 0
            style_loss = 0

            for cl in content_losses:
                content_loss += cl.loss
            for sl in style_losses:
                style_loss += sl.loss

            content_loss *= content_weight
            style_loss *= style_weight

            loss = content_loss + style_loss
            loss.backward()

            step += 1
            if step % 50 == 0 or step == NUM_STEPS:
                logger.info('Step %d/%d:', step, NUM_STEPS)
                logger.info('Style loss : %.2f Content loss: %.2f', style_loss.item(), content_loss.item())

            return content_loss + style_loss

        optimizer.step(closure)

    with torch.no_grad():
        # TODO: call this only once
        work_image.clamp_(0, 1)

    return work_image


def load_image(image_path):
    image = Image.open(image_path).convert('RGB')
    tensor = transforms.ToTensor()(image)
    size = tensor.shape[1:]
    long_edge = max(size)
    if long_edge > MAX_SIZE:
        scale = MAX_SIZE / long_edge
        size = [max(round(s * scale), 1) for s in size]
        tensor = transforms.Resize(size, interpolation=transforms.InterpolationMode.BICUBIC, antialias=True)(tensor)
    return tensor.unsqueeze(0).to(device)


def style_transfer(content_path, style_path, strength):
    content_image = load_image(content_path)
    style_image = load_image(style_path)
    style_weight = MAX_STYLE_WEIGHT * strength / 100
    output = run_style_transfer(content_image, style_image, CONTENT_WEIGHT, style_weight)
    return transforms.ToPILImage()(output[0])
