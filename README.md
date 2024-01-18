# PicStylist

## Resources
 - Digital Ocean
 - Cloudflare
 - Sentry
 - Portainer (optional)

### Tech notes
 - Cloudflare authenticated origin pulls: https://developers.cloudflare.com/ssl/origin-configuration/authenticated-origin-pull/set-up/zone-level/
 - Cloudflare prepend www to root domain: https://developers.cloudflare.com/rules/url-forwarding/single-redirects/examples/#redirect-all-requests-to-a-different-hostname
 - Portainer installation: https://docs.portainer.io/start/install-ce/server/docker/linux


## How it works
It does need a few words, so please bear with me.

Neural networks are typically structured in layers.
Each of these layers processes the results from the previous layer
and produces a result that is fed into the next layer.
The first layer processes the input data (in our case, an image),
and the last layer produces the final output (in our case, a stylized image).
The intermediate layers produce internal representations of the data.

In computer vision, most layers are typically "convolutional",
which means that they apply filters to their input,
similar to the filters we use in image processing software.
The difference is that we don't tell the network what filters to use.
It learns that on its own during training.

The training process works by feeding the network a (large) set of example images.
The network then produces a result for each image, and we compare its output to the desired output.
When the difference between the two is too large, we adjust the network's parameters (filters)
in the direction that would produce better results.
Then we repeat this process multiple times, producing better and better results after each step.

After the training, it turns out that the first layers of the network have learned to detect low-level features,
like lines and edges, while the last layers have learned to detect high-level features, like faces.
When we are building a network to detect what's in an image (called "image classification"),
the very last layers (the "head") weigh the presence or absence of the detected high-level features
and classify the image based on that.
For example, if it has eyes, ears, a long wet nose, long tongue and sharp teeth, but no wheels, it must be a dog.
But when it has wheels, doors and windows, it must be a car.
However, this is an oversimplification - we can even detect different dog breeds, and different vehicle types.

It also turns out that the middle layers of image classification networks can detect textures, or styles.
It is shiny metal, or it is wood, or brown fur. It has a pattern of stripes, or dots, or waves.
So we can modify an original image and style it like another image.
The final image will have the same subject and high-level structure as the original image,
but with the textures of the style image.
Since the style is represented by the output of the network's middle layers, it is just a set of numbers.
The same is true for the content, which is represented by the numbers in the output of the last layers.
Therefore, the task is to come up with an image, such that, when it passes through the network,
the middle layers produce an output close to their output for the style image,
and the last layers produce an output close to their output for the original image.
We start with the original image and pass it through a pre-trained network multiple times.
Each time, we measure the differences between:
 - the middle (texture) layer's output and the same layer's output when the network was given the style image
 - the last (content) layer's output and the same layer's output for the original image
Then we adjust the image in the direction that would reduce these differences.
Rinse and repeat until both differences are small enough, et voilà!

Pretty cool, right? But there's a catch. The process is computationally intensive and slow.
It can take minutes to style a single high-resolution image,
even when we already have a pre-trained image classification network.
For a desktop application, this may not be a problem, but who would wait minutes for a web page to load?
So to speed this up, we use another neural network, trained specifically for this task.
Before training, we use the above (slow) method to produce a (large) set of styled images.
Then, during training, we feed the network the original images, and gradually adjust it to produce results
close enough to the styled images.
After training, each time we need to style a new image, we feed it to the network only once,
and the result is a styled image, hopefully close to what the previous method would have produced.
This is much faster because it happens in one go and does not require multiple iterations.
It also requires less memory. It still needs a few seconds, but that's much better than minutes.
With good hardware and/or modest resolutions, it can work in real-time with videos.

For a (slightly) more mathematical explanation, see the end of this document.
If you want to know more, check out the [original paper](https://arxiv.org/abs/1508.06576) by Gatys et al.,
and the [fast style transfer paper](https://arxiv.org/abs/1705.06830) by Ghiasi et al.
A TensorFlow tutorial is available [here](https://www.tensorflow.org/tutorials/generative/style_transfer).
The pre-trained model, that we use here, is available on
[TensorFlow Hub](https://tfhub.dev/google/magenta/arbitrary-image-stylization-v1-256/2).

Cheers!


### Math details (optional)
The process of adjusting an image in the direction, that would improve the results, is called "gradient descent".
Adjusting the image actually means adjusting the RGB values of each pixel.
In mathematics, a gradient is the direction, in which a scalar function of multiple variables increases the fastest.
It is a vector of the partial derivatives of the function with respect to each of its variables.
In our case, the variables are the RGB values of each pixel.
But when training the network itself, the variables are the network's parameters (filters).
And the function is the "loss" or "cost" function, which measures the difference (or distance) between
the desired output and the network's actual output at the current step.
Again, it's an oversimplification - even for the same task,
one could use different loss functions for different purposes,
for example to tolerate or to penalise outliers in the output.
The algorithm to compute the gradient, in tolerable time, is called "backpropagation".
Because each layer's output is a function of the previous layer's output,
this algorithm uses the "chain rule" of calculus and starts from the last layer,
recursing backwards through the layers, and multiplying partial derivatives at each step.
Hence the name "backpropagation". What's ingenious about it is that it only needs to traverse the network once.
By itself, computing derivatives is a simple task in math.
And the functions, computed by the layers are usually simple - (matrix) multiplications and additions.
But there are many of them. Also, modern neural networks have millions, or even many billions of parameters.
This makes the task impossible for a human to do by hand, but in software, there exist tools to automate it.
After the gradient is computed, all that is left to do is to adjust the parameters.
And because the gradient is the direction of fastest increase of the cost function,
we adjust the parameters in the opposite direction - by subtracting the gradient.
Hence the name "gradient descent".
It's like going downhill to return home when you're lost in a mountain'.
It's dark and foggy, so you can't see, but you can feel the slope of the ground with your feet.
Then you just follow the slope downward, step by step.
Now, imagine that you are a super human and can take really large steps.
You're also hungry, so you want to return home fast!
You may save time by taking huge steps, but if you may also end up on the hill on the other side of your home.
Same for gradient descent - we only know the first partial derivatives,
so we need to take moderate steps to avoid overshooting the minimum of the cost function.
This example is only two-dimensional (the height of the ground being the 3rd dimension).
Neural networks have many parameters, so their "home" is in much higher-dimensional space.
We can't imagine or visualize anything above 3D (or 4D if you imagine time progressing),
but for the network it's just some more numbers.
And it turns out that working in a high-dimensional space even has benefits,
because many of our intuitions from low-dimensional spaces are no longer valid.
For example, there is a very low probability that we would end up in a local minimum,
because this probability decreases exponentially with the number of dimensions.
