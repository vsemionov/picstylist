# PicStylist

## Resources
 - Digital Ocean
 - Cloudflare
 - Sentry
 - Portainer (optional)

### Tech Notes
 - Cloudflare authenticated origin pulls: https://developers.cloudflare.com/ssl/origin-configuration/authenticated-origin-pull/set-up/zone-level/
 - Cloudflare prepend www to root domain: https://developers.cloudflare.com/rules/url-forwarding/single-redirects/examples/#redirect-all-requests-to-a-different-hostname
 - Portainer installation: https://docs.portainer.io/start/install-ce/server/docker/linux


## How It Works
Neural networks are typically structured in layers.
Each of these layers processes the results from the previous layer
and produces a result that is fed into the next layer.
The first layer processes the input data (in our case, an image),
and the last layer produces the final output (in our case, a stylized image).
The intermediate layers produce internal representations of the data.

In computer vision, most layers are typically convolutional,
which means that they apply filters to their input,
similar to the filters we use in image processing software.
The difference is that we don't tell the network what filters to use.
It learns that on its own during training.

The training process works by feeding the network a (large) set if example images.
The network then produces a result for each image, and we compare its output to the desired output.
When the difference between the two is too large, we adjust the network's parameters (filters)
in the direction that would produce better results.
Then we repeat this process multiple times, producing better and better results after each step.

After the training, it turns out that the first layers of the network have learned to detect low-level features,
like edges, while the last layers have learned to detect high-level features, like faces.
When we are building a network to detect what's in an image (called "image classification"),
the very last layers (the "head") weigh the presence or absence of the detected high-level features
and classify the image based on that.
For example, if it has eyes, ears, a long wet nose, long tongue and sharp teeth, but no wheels, it must be a dog.
But when it has wheels, doors and windows, it must be a car.
However, this is an oversimplification - we can even detect different dog breeds, and different vehicle types.

It also turns out that the middle layers of trained image classification networks can detect textures, or styles.
It is shiny metal, or it is wood, or brown fur.
So we can modify an original image and style it like another image.
The final image will have the same subject and high-level structure as the original image,
but with the textures of the style image.
Since the style is represented by the output of the network's middle layers, it is just a set of numbers.
The styling process works by passing the image through a pre-trained image classification network multiple times.
Each time, we measure the difference between:
 - the middle (texture) layer's output and the same layer's output when the network was given the style image
 - the last (content) layer's output and the same layer's output for the original image
Then we adjust the input image in the direction that would reduce the difference.
Rinse and repeat until both differences are small enough, and voilà!

Pretty cool, right? But there is a catch. The process is computationally intensive and slow.
It can take minutes to style a single high-resolution image,
even when we already have a pre-trained image classification network.
For a desktop application, this may not be a problem, but who would wait minutes for a web page?
So to speed this up, we use another neural network, trained specifically for this task.
Before training, we use the above (slow) method to produce a (large) set of styled images.
Then, during training, we feed the network the original images, and gradually adjust it to produce results
close enough to the styled images.
After training, each time we need to style a new image, we feed it to the network only once,
and the result is a styled image, hopefully close to what the previous method would have produced.
But this is much faster because it happens in one go and does not require multiple iterations.
It also requires less memory. It still needs a few seconds, but that's much better than minutes.
And with good hardware and/or modest image sizes, it can even work in real time and can be applied to videos.

If you want to know more, check out the [original paper](https://arxiv.org/abs/1508.06576) by Gatys et al.,
and the [fast style transfer paper](https://arxiv.org/abs/1705.06830) by Ghiasi et al.
The pre-trained model we use is available on
[TensorFlow Hub](https://tfhub.dev/google/magenta/arbitrary-image-stylization-v1-256/2).

Cheers!
