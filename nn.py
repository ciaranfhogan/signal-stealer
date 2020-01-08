import numpy as np
import matplotlib.pyplot as plt
import time
import sys
import cv2
import uuid
import random
import math
import act
from abc import ABC, abstractmethod

def _randomWeights(rows, cols):
    return np.random.rand(rows, cols) * 2.0 - 1.0

def _meanSquaredError(error):
    return np.dot(error[0], error[0].T) / len(error[0])

class SimpleFFNN:
    
    _fps = 2

    _weights = []
    _act = []
    _inputs = _target = _feed = _feedAct = None

    _xAxisOverview, _yAxisOverview = [], []
    _xAxisLive, _yAxisLive = [], []
    _targetXValues = 50
    _expStep, _step = 1, 100
    _liveValues = 100

    def __init__(self, *nodesPerLayer, learningRate=1, seed=None):
        
        # Keep results consistent
        if seed is not None:
            np.random.seed(seed)
        else:
            np.random.seed(hash(uuid.uuid4()) % (2**32 - 1))

        self._learningRate = learningRate
        self._numOfLayers = len(nodesPerLayer)
        self._nodesPerLayer = nodesPerLayer

        for i in range(self._numOfLayers-1):
            nodesInCurLayer = nodesPerLayer[i]
            nodesInNextLayer = nodesPerLayer[i+1]
            self._weights.append(
                _randomWeights(nodesInCurLayer, nodesInNextLayer))
            self._act.append(act.LeakyReluAF())
        
        self._act.pop(-1)
        self._act.append(act.AtanAF())

    def _gradientDescentHelper(self, layer, error):

        # BASE CASE: output layer
        if layer == self._numOfLayers-1:
            return error * self._act[layer-1].computeDer(self._feed[layer])
        
        # RECURSION
        result = np.dot(
            self._gradientDescentHelper(layer+1, error),
            self._weights[layer].T
        ) * self._act[layer-1].computeDer(self._feed[layer])
        
        return result
    
    def _gradientDescent(self, layer, error):

        result = np.dot(
            self._feedAct[layer].T,
            self._gradientDescentHelper(layer+1, error)
        )

        return result

    def backPropagation(self, error):

        for k in range(self._numOfLayers-1):
            self._weights[k] += self._gradientDescent(k, error) * self._learningRate

    def forwardPropagation(self, inputs):

        self._feed[0] = self._feedAct[0] = inputs
        for i in range(1, self._numOfLayers):
            self._feed[i] = np.dot(self._feedAct[i-1], self._weights[i-1])
            self._feedAct[i] = self._act[i-1].compute(self._feed[i])

        return self._feedAct[-1]

    def setTrainingData(self, inputs, target):

        self._numOfSamples = len(inputs)

        self._inputs = inputs
        self._target = target

        self._feed = []
        self._feedAct = []

        # Add an array of zeros with the same dimensions as the inputs
        self._feed.append(np.zeros((len(inputs), len(inputs[0]))))
        self._feedAct.append(np.zeros((len(inputs), len(inputs[0]))))
        for i in range(1, self._numOfLayers):
            shape = (self._nodesPerLayer[i] * self._numOfSamples, len(self._weights[i-1]))
            self._feed.append(np.zeros(shape))
            self._feedAct.append(np.zeros(shape))
        

    def train(self, epoch, graph=True, showOutput=False, showWeights=False):

        assert self._inputs is not None and self._target is not None, \
            "No training data. Make sure you call 'setTrainingData' before training."

        if graph: self._initGraph()

        lastDrawTime = 0

        for i in range(epoch):
            
            # Update the learning rate
            # TODO: remoke this -- give user more control
            if (i + 1) % (epoch // 10) == 0:
                print('Learning rate reduced from ', self._learningRate, end='')
                self._learningRate *= 0.8
                print(' to ', self._learningRate)

            # Propagate the input through the network and get
            # the result
            result = self.forwardPropagation(self._inputs)
            # Determine the error between the result and the 
            # target result
            error = self._target - result
            # Update the weights to reduce this error
            self.backPropagation(error)

            # Draw any visualizations
            if graph: self._graphPoint(i, _meanSquaredError(error))
            if time.time() - lastDrawTime > (1.0 / self._fps):
                if showOutput: self._visualizeOutput()
                if showWeights: self._visualizeWeights()
                if graph: self._drawGraph()
                lastDrawTime = time.time()
    
    def _initGraph(self):

        self._xAxisOverview.clear()
        self._yAxisOverview.clear()
        self._xAxisLive.clear()
        self._yAxisLive.clear()
        self._step = 1

    def _graphPoint(self, x, y):

        if x % self._step == 0:
            self._xAxisLive.append(x)
            self._yAxisLive.append(y)
            if len(self._xAxisLive) > self._liveValues:
                self._xAxisLive.pop(0)
                self._yAxisLive.pop(0)
        if x % self._expStep == 0:
            # Add the point to the graph
            self._xAxisOverview.append(x)
            self._yAxisOverview.append(y)
            # If the list has grown to two times the
            # target size, halve it
            if len(self._xAxisOverview) % (self._targetXValues * 2) == 0:
                #print('Halving array...')
                # Remove every other element
                self._xAxisOverview = self._xAxisOverview[::2]
                self._yAxisOverview = self._yAxisOverview[::2]
                self._expStep *= 2
    
    def _drawGraph(self):

        plt.clf()

        plt.subplot(3, 1, 1)
        plt.title('Training Overview')
        plt.xlabel('Iteration')
        plt.ylabel('Error (MSE)')
        plt.plot(self._xAxisOverview, self._yAxisOverview, color='red')

        plt.subplot(3, 1, 3)
        plt.title('Live Training')
        plt.xlabel('Iteration')
        plt.ylabel('Error (MSE)')
        plt.plot(self._xAxisLive, self._yAxisLive, color='red')

        plt.pause(0.0001)

    def _visualizeOutput(self):

        width, height = 20, 20
        img = np.full((width, height, 3), 255, np.uint8)

        values = [[self.forwardPropagation([x / (width-1), y / (height-1)])
            for y in range(height)]
            for x in range(width)]
        largest = max(max(i) for i in values)
        smallest = min(min(i) for i in values)

        for x in range(width):
            for y in range(height):
                normalized = (values[x][y] - smallest) / (largest - smallest)
                c = int(normalized * 255)
                img[x][y] = (c, c, c)
        
        resized = cv2.resize(img, (256, 256))

        cv2.imshow('Output Visualization', resized)
        cv2.waitKey(20)
    
    def _visualizeWeights(self):

        width, height = 256 * 2, 256

        img = np.full((height, width, 3), 255, np.uint8)

        buffer = 4
        minLineWidth = 1
        orange = (233, 121, 67)
        blue = (67, 125, 233)
        grey = (34, 40, 49)
        
        maxNumOfNodes = max(self._nodesPerLayer)
        nodeRadius = height // (buffer * 2 * maxNumOfNodes)

        maxLineWidth = nodeRadius // 4

        verticalSpacing = buffer * nodeRadius * 2
        horizontalSpacing = width // len(self._nodesPerLayer)

        # Draw the weights
        maxWeight = max(np.amax(w) for w in self._weights)
        minWeight = min(np.amin(w) for w in self._weights)

        for layer in range(len(self._weights)):
            w = self._weights[layer]
            leftX = horizontalSpacing * layer + horizontalSpacing // 2
            rightX = horizontalSpacing * (layer + 1) + horizontalSpacing // 2
            for leftNode in range(len(w)):
                for rightNode in range(len(w[leftNode])):
                    leftY = verticalSpacing * leftNode + verticalSpacing // 2 - nodeRadius // 2
                    rightY = verticalSpacing * rightNode + verticalSpacing // 2 - nodeRadius // 2
                    strength = (w[leftNode][rightNode] -
                                minWeight) / (maxWeight - minWeight)
                    width = int((maxLineWidth - minLineWidth)
                                * strength + minLineWidth)
                    if w[leftNode][rightNode] >= 0:
                        color = tuple([int((1 - strength) * (255 - x) + x) for x in orange])
                    else:
                        color = tuple([int((1 - strength) * (255 - x) + x) for x in blue])
                    cv2.line(img, (leftX, leftY), (rightX, rightY), color, width, cv2.LINE_AA)

        # Draw the nodes
        for layer in range(len(self._nodesPerLayer)):
            for node in range(self._nodesPerLayer[layer]):
                x = horizontalSpacing * layer + horizontalSpacing // 2
                y = verticalSpacing * node + verticalSpacing // 2 - nodeRadius // 2
                cv2.circle(img, (x, y), nodeRadius, grey, cv2.FILLED, cv2.LINE_AA)
        
        cv2.imshow('Weight Visualization', img)
        cv2.waitKey(20)




    

class FeedForwardNN2:
    '''
    A simple implementation of a feed forward neural network.
    '''

    def __init__(self, inputNodes, hiddenNodes1, hiddenNodes2, outputNodes, learningRate=1.0, seed=None):
        '''
        Create a new feed forward neural network, with the specified
        number of nodes initialized with random values.
        '''
        # Keep results consistent
        if seed is not None:
            np.random.seed(seed)
        else:
            np.random.seed(hash(uuid.uuid4()) % (2**32 - 1))

        self._learningRate = learningRate

        self._inputNodes = inputNodes
        self._outputNodes = outputNodes

        self._numOfNodes = [inputNodes,
                            hiddenNodes1, hiddenNodes2, outputNodes]

        # Initialize the weights with random values
        self._weights = []
        self._weights.append(np.random.rand(
            inputNodes, hiddenNodes1) * 2.0 - 1.0)
        self._weights.append(np.random.rand(
            hiddenNodes1, hiddenNodes2) * 2.0 - 1.0)
        self._weights.append(np.random.rand(
            hiddenNodes2, outputNodes) * 2.0 - 1.0)
        self._bias = []
        self._bias.append(0)
        self._bias.append(0)
        self._bias.append(0)

    def _sigmoid(self, z):
        '''
        An activation function returning values in the
        interval (0, 1)
        '''
        # return np.arctan(z)
        # return np.tanh(z)
        return 1.0 / (1.0 + np.exp(-z))

    def _sigmoidDerivative(self, z):
        '''
        The derivative of the sigmoid function.
        i.e. the direction the sigmoid function increases.
        '''
        # return 1 / (z**2 + 1)
        # return 1.0 - np.tanh(z)**2
        return self._sigmoid(z) * (1.0 - self._sigmoid(z))

    def _relu(self, x):
        '''
        The master of stupidity
        '''
        z = np.copy(x)
        return z * (z > 0)

    def _reluDerivative(self, x):
        '''
        Does something important. I dunno Google it.
        '''
        z = np.copy(x)
        return 1.0 * (z > 0)

    def _leakyRelu(self, x):
        z = np.copy(x)
        return np.where(z > 0, z, z * 0.01)

    def _leakyReluDerivative(self, x):
        z = np.copy(x)
        return np.where(z > 0, 1, 0.01)

    def _atan(self, x):
        return np.arctan(x)

    def _atanDerivative(self, x):
        return 1.0 / (x**2 + 1.0)

    # https://stackoverflow.com/questions/47377222/cross-entropy-function-python
    def _crossEntropy(self, predictions, targets, epsilon=1e-12):
        """
        Computes cross entropy between targets (encoded as one-hot vectors)
        and predictions. 
        Input: predictions (N, k) ndarray
            targets (N, k) ndarray        
        Returns: scalar
        """
        predictions = np.clip(predictions, epsilon, 1. - epsilon)
        N = predictions.shape[0]
        ce = -np.sum(targets*np.log(predictions+1e-9))/N
        return ce

    def gradientDescent(self, inputs, target, iterations, graph=True, draw=False):
        '''
        Trains the network. But you already knew that right?
        '''

        # Check the the inputs and target dimensions make sense.
        assert len(inputs) == len(
            target), 'Each input should have a target value.'
        assert len(
            inputs[0]) == self._inputNodes, 'The number of inputs does not match the number of input nodes.'
        assert len(
            target[0]) == self._outputNodes, 'The number of outputs does not match the number of output nodes.'

        lastDrawTime = 0

        if graph:
            xAxis = []
            yAxis = []
            plt.title('Training')
            plt.xlabel('Iteration')
            plt.ylabel('Error (MSE)')
            #plt.ylim(0, 1)
            # plt.xlim(0,iterations)

        print("Training", end='')
        for i in range(iterations):

            if i % (iterations // 10) == 0:
                print('.', end='')
                sys.stdout.flush()

            # FORWARD PASS
            # Feed the values through the network and the calculate the
            # error between the result <feed2Activated> and the target
            # result <target>
            # DONT FORGET TO CHANGE THE ACTIVATION FUCNTIONS IN THE
            # PREDICTION METHOD AS WELL!!!!!!
            feed1 = np.dot(inputs, self._weights[0])# + self._bias[0]
            feed1Activated = self._leakyRelu(feed1)
            feed2 = np.dot(feed1Activated, self._weights[1])# + self._bias[1]
            feed2Activated = self._leakyRelu(feed2)
            feed3 = np.dot(feed2Activated, self._weights[2])# + self._bias[2]
            feed3Activated = self._atan(feed3)

            error = target - feed3Activated
            #print(error, target, feed3Activated)
            #error = np.array([self._crossEntropy(feed3Activated[i], target[i]) for i in range(len(target))]).T

            # BACK PROPAGATION
            # Calculate the gradient for the weights
            layers3to2Gradient = np.dot(
                feed2Activated.T,
                error * self._atanDerivative(feed3)
            )
            layers3to2Bias = error * self._atanDerivative(feed3)

            layers3to1Gradient = np.dot(
                feed1Activated.T,
                np.dot(
                    error * self._atanDerivative(feed3),
                    self._weights[2].T
                ) * self._leakyReluDerivative(feed2)
            )
            layers3to1Bias = np.dot(
                error * self._atanDerivative(feed3),
                self._weights[2].T
            ) * self._leakyReluDerivative(feed2)

            layers3to0Gradient = np.dot(
                inputs.T,
                np.dot(
                    np.dot(
                        error * self._atanDerivative(feed3),
                        self._weights[2].T
                    ) * self._leakyReluDerivative(feed2),
                    self._weights[1].T
                ) * self._leakyReluDerivative(feed1)
            )
            layers3to0Bias = np.dot(
                np.dot(
                    error * self._atanDerivative(feed3),
                    self._weights[2].T
                ) * self._leakyReluDerivative(feed2),
                self._weights[1].T
            ) * self._leakyReluDerivative(feed1)

            # Update the weights
            self._weights[2] += layers3to2Gradient * self._learningRate
            self._weights[1] += layers3to1Gradient * self._learningRate
            self._weights[0] += layers3to0Gradient * self._learningRate
            self._bias[2] += layers3to2Bias * self._learningRate
            self._bias[1] += layers3to1Bias * self._learningRate
            self._bias[0] += layers3to0Bias * self._learningRate

            # Plot the graph every 1/30th of a second
            if time.time() - lastDrawTime > (1.0 / 30.0):
                if graph:
                    xAxis.append(i)
                    yAxis.append(self.meanSquaredError(error))
                    plt.plot(xAxis, yAxis, color='red')
                    plt.pause(0.0001)
                if draw:
                    self._draw()
                lastDrawTime = time.time()

        if graph:
            plt.plot(xAxis, yAxis, color='black')
            plt.show()

        print(' Done!')

    def prediction(self, inputs):
        '''
        Feeds the input through the neural network and returns
        what is the predicted result.
        i.e. Forward propagation
        '''

        x1 = self._leakyRelu(np.dot(inputs, self._weights[0]))
        x2 = self._leakyRelu(np.dot(x1, self._weights[1]))
        x3 = self._atan(np.dot(x2, self._weights[2]))

        return x3

    def meanSquaredError(self, error):
        return np.dot(error[0], error[0].T) / len(error[0])

    def _draw(self):

        width, height = 1024, 1024

        img = np.full((width, height, 3), 255, np.uint8)

        buffer = 3
        minLineWidth = 1

        maxNumOfNodes = max(self._numOfNodes)
        nodeRadius = height // (buffer * 2 * maxNumOfNodes)

        maxLineWidth = nodeRadius // 2

        verticalSpacing = buffer * nodeRadius * 2
        horizontalSpacing = width // len(self._numOfNodes)

        # Draw the weights
        maxWeight = max(np.amax(w) for w in self._weights)
        minWeight = min(np.amin(w) for w in self._weights)

        for layer in range(len(self._weights)):
            w = self._weights[layer]
            leftX = horizontalSpacing * layer + horizontalSpacing // 2
            rightX = horizontalSpacing * (layer + 1) + horizontalSpacing // 2
            for leftNode in range(len(w)):
                for rightNode in range(len(w[leftNode])):
                    leftY = verticalSpacing * leftNode + verticalSpacing + nodeRadius * 2
                    rightY = verticalSpacing * rightNode + verticalSpacing + nodeRadius * 2
                    strength = (w[leftNode][rightNode] -
                                minWeight) / (maxWeight - minWeight)
                    width = int((maxLineWidth - minLineWidth)
                                * strength + minLineWidth)

                    cv2.line(img, (leftX, leftY), (rightX, rightY), (255, 255 *
                                                                     (1-strength), 255 * (1-strength)), width, cv2.LINE_AA)

        # Draw the nodes
        for layer in range(len(self._numOfNodes)):
            for node in range(self._numOfNodes[layer]):
                x = horizontalSpacing * layer + horizontalSpacing // 2
                y = verticalSpacing * node + verticalSpacing + nodeRadius * 2
                cv2.circle(img, (x, y), nodeRadius,
                           (15, 15, 15), cv2.FILLED, cv2.LINE_AA)

        nodes = np.asfortranarray([
            [0.0, 0.625, 1.0],
            [0.0, 0.5, 0.5],
        ])
        
        # curve = bezier.Curve(nodes, degree=2)
        # points = curve.evaluate(0.75)
        # axis = curve.plot(10)
        # curve.evaluate_multi

        cv2.imshow('Training Visualization', img)
        cv2.waitKey(20)


# Based on: https://towardsdatascience.com/a-step-by-step-implementation-of-gradient-descent-and-backpropagation-d58bda486110
class FeedForwardNN:
    '''
    A simple implementation of a feed forward neural network.
    '''

    def __init__(self, inputNodes, hiddenNodes, outputNodes, learningRate=1.0, seed=314159):
        '''
        Create a new feed forward neural network, with the specified
        number of nodes initialized with random values.
        '''
        # Keep results consistent
        np.random.seed(seed)

        self._learningRate = learningRate

        self._inputNodes = inputNodes
        self._hiddenNodes = hiddenNodes
        self._outputNodes = outputNodes

        # Initialize the weights with random values
        self.inputToHiddenWeights = np.random.rand(inputNodes, hiddenNodes)
        self.hiddenToOutputWeights = np.random.rand(hiddenNodes, outputNodes)

    def _sigmoid(self, z):
        '''
        An activation function returning values in the
        interval (0, 1)
        '''
        # return np.tanh(z)
        return 1.0 / (1.0 + np.exp(-z))

    def _sigmoidDerivative(self, z):
        '''
        The derivative of the sigmoid function.
        i.e. the direction the sigmoid function increases.
        '''
        # return 1.0 - np.tanh(z)**2
        return self._sigmoid(z) * (1.0 - self._sigmoid(z))

    def gradientDescent(self, inputs, target, iterations):
        '''
        Trains the network.
        '''

        # Check the the inputs and target dimensions make sense.
        assert len(inputs) == len(
            target), 'Each input should have a target value.'
        assert len(
            inputs[0]) == self._inputNodes, 'The number of inputs does not match the number of input nodes.'
        assert len(
            target[0]) == self._outputNodes, 'The number of outputs does not match the number of output nodes.'

        xAxis = []
        yAxis = []

        print("Training", end='')
        for i in range(iterations):

            if i % (iterations // 10) == 0:
                print('.', end='')

            # Feed the values through the network and the calculate the
            # error between the result <feed2Activated> and the target
            # result <target>
            feed1 = np.dot(inputs, self.inputToHiddenWeights)
            feed1Activated = self._sigmoid(feed1)
            feed2 = np.dot(feed1Activated, self.hiddenToOutputWeights)
            feed2Activated = self._sigmoid(feed2)
            error = target - feed2Activated

            xAxis.append(i)
            yAxis.append(np.dot(error[0], error[0].T))

            # Calculate the gradient for the weights
            hiddenToOutputGradient = np.dot(
                feed1Activated.T,
                error * self._sigmoidDerivative(feed2)
            )

            inputToHiddenGradient = np.dot(
                inputs.T,
                np.dot(
                    error * self._sigmoidDerivative(feed2),
                    self.hiddenToOutputWeights.T
                ) * self._sigmoidDerivative(feed1)
            )

            # Update the weights
            self.inputToHiddenWeights   += inputToHiddenGradient * self._learningRate
            self.hiddenToOutputWeights  += hiddenToOutputGradient * self._learningRate

        print(' Done!')
        plt.plot(xAxis, yAxis)
        plt.show()

    def prediction(self, inputs):
        '''
        Feeds the input through the neural network and returns
        what is the predicted result.
        i.e. Forward propagation
        '''

        x1 = self._sigmoid(np.dot(inputs, self.inputToHiddenWeights))
        x2 = self._sigmoid(np.dot(x1, self.hiddenToOutputWeights))

        return x2
