import matplotlib.pyplot as plt
import numpy as np
import numpy.random as rd
import tensorflow as tf
from time import time

from hebb.util import *
from hebb.models import *
from hebb.config import params

FLAGS = tf.app.flags.FLAGS

# Experiment parameters
dt = 1  # time step in ms
input_f0 = FLAGS.f0 / 1000  # input firing rate in kHz in coherence with the usage of ms for time
regularization_f0 = FLAGS.reg_rate / 1000  # desired average firing rate in kHz
tau_m = tau_m_readout = 30
thr = FLAGS.thr
save_dir = '/home/cwseitz/Desktop/experiment/'


cell = ExInLIF(n_in=FLAGS.n_in, n_rec=FLAGS.n_rec,
                tau=tau_m, thr=thr,dt=dt, p_e=FLAGS.p_e,
                dampening_factor=FLAGS.dampening_factor,
                stop_z_gradients=FLAGS.stop_z_gradients)

frozen_poisson_noise_input = np.random.rand(FLAGS.n_batch, FLAGS.seq_len, FLAGS.n_in) < dt * input_f0
input = tf.constant(frozen_poisson_noise_input, dtype=tf.float32) #only to excitatory units

#Tensorflow ops that simulates the RNN
outs, final_state = tf.nn.dynamic_rnn(cell, input, dtype=tf.float32)
z_e, z_i, v_e, v_i = outs


with tf.name_scope('SpikeRegularizationLoss'):

    #z = tf.concat([z_e, z_i], axis=-1)
    av = tf.reduce_sum(z_e, axis=0)
    average_firing_rate_error = av - regularization_f0
    sl_1 = tf.reduce_mean(average_firing_rate_error ** 2)

#Gradients
overall_loss = sl_1
var_list = [cell.w_e_in, cell.w_ee, cell.w_ei, cell.w_ie, cell.w_ii]
true_gradients = tf.gradients(overall_loss, var_list)
w_e_in_grad, w_ee_grad, w_ei_grad, w_ie_grad, w_ii_grad = true_gradients

#Optimizer
with tf.name_scope("Optimization"):
    opt = tf.train.GradientDescentOptimizer(learning_rate=FLAGS.learning_rate)
    grads_and_vars = [(g, v) for g, v in zip(true_gradients, var_list)]
    train_step = opt.apply_gradients(grads_and_vars)

sess = tf.Session()
sess.run(tf.global_variables_initializer())

results_tensors = {
    'av': av,
    'sl_1': sl_1,
    'z_e': z_e,
    'z_i': z_i,
    'v_e': v_e,
    'v_i': v_i,
    'w_e_in': cell.w_e_in,
    'w_ee': cell.w_ee,
    'w_ei': cell.w_ei,
    'w_ie': cell.w_ie,
    'w_ii': cell.w_ii,
    'w_e_in_grad': w_e_in_grad,
    'w_ee_grad': w_ee_grad,
    'w_ei_grad': w_ei_grad,
    'w_ie_grad': w_ie_grad,
    'w_ii_grad': w_ii_grad,
    'input': input
}


def train():

    t_train = 0
    clean_data_dir()

    for k_iter in range(FLAGS.n_iter):
        t0 = time()
        sess.run(train_step)
        t_train = time() - t0
        print(f'Training iteration: {k_iter}')

        if np.mod(k_iter, FLAGS.print_every) == 0:
            t0 = time()

            results_values = sess.run(results_tensors)
            save_tensors(results_values, str(k_iter), save_dir=save_dir)
            t_valid = time() - t0

train()