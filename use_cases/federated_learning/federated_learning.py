#!/usr/bin/env python3

# CNN mode detection
from use_cases.federated_learning.Mode_Detection_CNN import *
# Custom federated hook
from layers.communication.federated_hook import _FederatedHook
# Helper libraries
import os
import numpy as np
from time import time
import tensorflow as tf

BATCH_SIZE = 16
EPOCHS = 250
INTERVAL_STEPS = 1  # Steps between averages
WAIT_TIME = 15  # How many seconds to wait for new workers to connect
CHIEF_PUBLIC_IP = 'localhost:7777'  # Public IP of the chief worker
CHIEF_PRIVATE_IP = 'localhost:7777'  # Private IP of the chief worker

flags = tf.app.flags

flags.DEFINE_boolean("is_chief", False, "True if this worker is chief")
flags.DEFINE_string("name", None, "name of the node in the BSMD")
flags.DEFINE_string("domain", None, "name of the domain")
flags.DEFINE_string("ip", None, "ip address for connecting to the BSMD")
flags.DEFINE_string("private_key", None, "private ket of the node")
flags.DEFINE_string("file_X", None, "X information file of the node")
flags.DEFINE_string("file_Y", None, "Y information file of the node")

# Disable GPU for all workers in local testing.
# Enable it when testing in different computers
os.environ['CUDA_VISIBLE_DEVICES'] = ''

# Create the custom hook
FLAGS = flags.FLAGS

list_of_workers = ['worker1', 'worker2', 'worker3', 'worker4', 'worker5', 'worker6', 'worker7', 'worker8', 'worker9']

federated_hook = _FederatedHook(FLAGS.is_chief, FLAGS.name, CHIEF_PRIVATE_IP, CHIEF_PUBLIC_IP, FLAGS.private_key,
                                list_of_workers, FLAGS.domain, FLAGS.ip, WAIT_TIME, INTERVAL_STEPS)

# parameters definition
num_channels_ensemble = [5]
num_filters_ensemble = []
filters_size_ensemble = []
num_stride_maxpool_ensemble = []
num_stride_conv2d_ensemble = []
maxpool_size_ensemble = []

# The data structures in the following data files are different from those in ensemble paper
X_train = np.load("use_cases/federated_learning/train_sets/{}.npy".format(FLAGS.file_X))
Y_train = np.load("use_cases/federated_learning/train_sets/{}.npy".format(FLAGS.file_Y))

# You can safely tune this variable
SHUFFLE_SIZE = X_train.shape[0]

Y_onehot = np.zeros((Y_train.shape[0], 4))
Y_onehot[np.arange(Y_train.shape[0]), Y_train] = 1
Y_train = np.copy(Y_onehot)
print('Data loaded')

CHECKPOINT_DIR = 'logs_dir/federated_{}/{}'.format(FLAGS.worker_name, time())

global_step = tf.train.get_or_create_global_step()

# Define input pipeline, place these ops in the cpu
with tf.name_scope('dataset'), tf.device('/cpu:0'):
    # Placeholders for the iterator
    X_placeholder = tf.placeholder(tf.float32, shape=(None, seg_size, num_channels), name='X_placeholder')
    Y_placeholder = tf.placeholder(tf.float32, shape=[None, num_classes], name='Y_placeholder')
    minibatch_weights = tf.placeholder(tf.float32, shape=[None], name='minibatch_weights')
    batch_size = tf.placeholder(tf.int64, name='batch_size')
    shuffle_size = tf.placeholder(tf.int64, name='shuffle_size')

    # Create data set from numpy arrays, shuffle, repeat and batch
    dataset = tf.data.Dataset.from_tensor_slices((X_placeholder, Y_placeholder))
    dataset = dataset.shuffle(shuffle_size, reshuffle_each_iteration=True)
    dataset = dataset.repeat(EPOCHS)
    dataset = dataset.batch(batch_size)

    iterator = tf.data.Iterator.from_structure(dataset.output_types, dataset.output_shapes)
    dataset_init_op = iterator.make_initializer(dataset, name='dataset_init')
    X, y = iterator.get_next()

# Define our model
num_layers_ensemble, filters_size_ensemble, num_filters_ensemble, maxpool_size_ensemble, num_stride_conv2d_ensemble, \
num_stride_maxpool_ensemble, weights_ensemble = parameters_weights()

filters_size = filters_size_ensemble[0]
num_filters = num_filters_ensemble[0]
num_stride_conv2d = num_stride_conv2d_ensemble[0]
num_stride_maxpool = num_stride_maxpool_ensemble[0]
maxpool_size = maxpool_size_ensemble[0]
weights = weights_ensemble[0]

# Initialize parameters
parameters = initialize_parameters(weights)

# Forward propagation: Build the forward propagation in the tensorflow graph
predictions = forward_propagation(X, parameters, num_stride_conv2d, maxpool_size, num_stride_maxpool)

# Object to keep moving averages of our metrics (for tensorboard)
summary_averages = tf.train.ExponentialMovingAverage(0.9)

# Define cross_entropy loss
with tf.name_scope('loss'):
    # loss = tf.losses.softmax_cross_entropy(onehot_labels=y, logits=predictions, weights=minibatch_weights)
    print("type logits:", type(predictions))
    print("dim logits:", predictions.shape)

    print("type labels:", type(y))
    print("dim labels:", y.shape)
    # loss = tf.reduce_mean(keras.losses.sparse_categorical_crossentropy(y, predictions))
    # loss = tf.nn.sparse_softmax_cross_entropy_with_logits(labels=y, logits=predictions)
    loss = tf.losses.softmax_cross_entropy(onehot_labels=y, logits=predictions, weights=1)
    loss_averages_op = summary_averages.apply([loss])
    # Store moving average of the loss
    tf.summary.scalar('cross_entropy', summary_averages.average(loss))

# Define accuracy metric
with tf.name_scope('accuracy'):
    with tf.name_scope('correct_prediction'):
        # Compare prediction with actual label
        correct_prediction = tf.equal(tf.argmax(predictions, 1), tf.cast(tf.argmax(y, 1), tf.int64))
    # Average correct predictions in the current batch
    accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32), name='accuracy_metric')
    accuracy_averages_op = summary_averages.apply([accuracy])
    # Store moving average of the accuracy
    tf.summary.scalar('accuracy', summary_averages.average(accuracy))

with tf.name_scope('train'):
    # Make train_op dependent on moving averages ops. Otherwise they will be
    # disconnected from the graph
    with tf.control_dependencies([loss_averages_op, accuracy_averages_op]):
        train_op = tf.train.AdamOptimizer(0.001).minimize(loss, global_step=global_step)

SESS_CONFIG = tf.ConfigProto(allow_soft_placement=True, log_device_placement=False)

# make the batch size equal to the number of training routes
BATCH_SIZE = X_train.shape[0]
N_BATCHES = int(X_train.shape[0] / BATCH_SIZE)
LAST_STEP = int(N_BATCHES * EPOCHS)

SESS_CONFIG = tf.ConfigProto(allow_soft_placement=True, log_device_placement=False)


# Logger hook to keep track of the training
class _LoggerHook(tf.train.SessionRunHook):
    def begin(self):
        """ Run this in session begin """
        self._total_loss = 0
        self._total_acc = 0

    def before_run(self, run_context):
        """ Run this in session before_run """
        return tf.train.SessionRunArgs([loss, accuracy, global_step])

    def after_run(self, run_context, run_values):
        """ Run this in session after_run """
        loss_value, acc_value, step_value = run_values.results
        # print(loss_value, acc_value, step_value)
        self._total_loss += loss_value
        self._total_acc += acc_value

        if (step_value + 1) % N_BATCHES == 0:
            print("Epoch {}/{} - loss: {:.4f} - acc: {:.4f}".format(int(step_value / N_BATCHES), EPOCHS,
                                                                    self._total_loss / N_BATCHES,
                                                                    self._total_acc / N_BATCHES))
            self._total_loss = 0
            self._total_acc = 0


class _InitHook(tf.train.SessionRunHook):
    """ Hook to initialize the data set """

    def after_create_session(self, session, coord):
        """ Run this after creating session """
        session.run(dataset_init_op, feed_dict={X_placeholder: X_train, Y_placeholder: Y_train, batch_size: BATCH_SIZE,
                                                shuffle_size: SHUFFLE_SIZE})


with tf.name_scope('monitored_session'):
    with tf.train.MonitoredTrainingSession(checkpoint_dir=CHECKPOINT_DIR,
                                           hooks=[_LoggerHook(), _InitHook(), federated_hook], config=SESS_CONFIG,
                                           save_checkpoint_steps=N_BATCHES) as mon_sess:
        while not mon_sess.should_stop():
            mon_sess.run(train_op)