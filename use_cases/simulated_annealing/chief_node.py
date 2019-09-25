import rpyc
import random
import time
import json
import logging
from math import exp, log
from utils.iroha import set_detail_to_node, get_a_detail_written_by
from absl import app
from absl import flags

FLAGS = flags.FLAGS
flags.DEFINE_string('name', None, 'Your name')
flags.DEFINE_string('private_key', None, 'Your private key to sign transactions')

# Connect to the working nodes
workers_proxies = []
ports = [18861]
workers = []

for port in ports:
    worker_proxy = rpyc.connect('localhost', port, config={'allow_public_attrs': True})
    workers_proxies.append(worker_proxy)

def new_state(beta_car, beta_cost, beta_tt):
    """
    Computes a new beta using a random error. The new beta is part of the annealing process
    :param beta_car: beta parameter of the car
    :param beta_cost: beta parameter of the cost
    :param beta_tt: beta parameter of the travel time
    :return: beta plus an error
    """
    chose_beta = random.randint(1,3)
    error = random.uniform(-0.01, 0.01)
    if chose_beta == 1:
        new_beta_car = beta_car + error
        new_beta_cost = beta_cost
        new_beta_tt = beta_tt
    if chose_beta == 2:
        new_beta_car = beta_car
        new_beta_cost = beta_cost + error
        new_beta_tt = beta_tt
    if chose_beta == 3:
        new_beta_car = beta_car
        new_beta_cost = beta_cost
        new_beta_tt = beta_tt + error
    return new_beta_car, new_beta_cost, new_beta_tt


def acceptance_probability(old_cost, new_cost, t):
    """
    Acceptance probability that the new cost improves the old cost.
    Part of the annealing process
    :param old_cost: old cost obtained from the slave nodes
    :param new_cost: new cost obtained from the slave nodes. The new cost use the parameter beta plus an error
    :param t: temperature of the annealing process
    :return: probability that the new cost improves the old cost
    """
    ap = exp((new_cost - old_cost) / t)
    return ap


# this model is send to all wokers
def model(beta_car, beta_cost, beta_tt, is_car, is_train, car_cost, car_tt, train_cost, train_tt):
    prob_car = exp(beta_car + beta_cost * (car_cost - train_cost) + beta_tt * (car_tt - train_tt)) / \
               (1 + exp(beta_car + beta_cost * (car_cost - train_cost) + beta_tt * (car_tt - train_tt)))
    observation = log(is_car * prob_car + is_train * (1 - prob_car))
    return observation



def main(argv):
    """
    Simulated annealing algorithm for solving the loglikehood choice model.
    1. Use the blockchain to send the model to the worker nodes.
    2. Use the blockchain to receive the cost from the worker nodes.
    3. By using simulated annealing and sending-receiving information the master node solves the loglikehood choice
    model without the need of personal information
    :param beta_car: beta parameter of the car
    :param beta_cost: beta parameter of the cost
    :param beta_tt: beta parameter of the travel time
    """
    beta_car = .00123
    beta_cost = .00664
    beta_tt = .006463
    solutions = []
    betas_car = []
    betas_cost = []
    betas_tt = []
    cost = 0
    cost_i = 0
    x = 0
    betas = str(beta_car) + ',' + str(beta_cost) + ',' + str(beta_tt)

    # send parameters to workers
    for worker in workers:
        # set_detail_to_node(sender, receiver, private_key, detail_key, detail_value, domain, ip):
        set_detail_to_node(FLAGS.name, worker, FLAGS.private_key, 'betas', betas, FLAGS.domain, FLAGS.ip)

    # start workers
    for proxy in workers_proxies:
        # compute_cost(self, writer, domain, ip, model):
        proxy.root.compute_cost(FLAGS.name, FLAGS.domain, FLAGS.ip, model)
    all_cost = []

    # get cost from all workers
    for worker in workers:
        b = get_a_detail_written_by(FLAGS.name, worker, FLAGS.private_key, 'cost', FLAGS.domain, FLAGS.ip)
        result = json.loads(b)
        from_node = worker + '@' + FLAGS.domain
        c = result[from_node]['cost']
        all_cost.append(float(c))
    # added cost of all workers
    initial_cost = sum(all_cost)

    print('initial solution = ', initial_cost)
    print('initial beta_car = ', beta_car)
    print('initial beta_cost = ', beta_cost)
    print('initial beta_tt = ', beta_tt)
    betas_car.append(beta_car)
    betas_cost.append(beta_cost)
    betas_tt.append(beta_tt)
    solutions.append(cost)
    temp = 1.0
    temp_min = 0.00001
    alpha = 0.9
    j = 0
    while temp > temp_min:
        i = 1
        while i <= 500:
            new_beta_car, new_beta_cost, new_beta_tt = new_state(beta_car, beta_cost, beta_tt)
            betas = str(new_beta_car) + ',' + str(new_beta_cost) + ',' + str(new_beta_tt)
            # send parameters to workers
            for worker in workers:
                # set_detail_to_node(sender, receiver, private_key, detail_key, detail_value, domain, ip):
                set_detail_to_node(FLAGS.name, worker, FLAGS.private_key, 'betas', betas, FLAGS.domain, FLAGS.ip)

            # get cost from all workers
            all_cost = []
            for worker in workers:
                b = get_a_detail_written_by(FLAGS.name, worker, FLAGS.private_key, 'cost', FLAGS.domain, FLAGS.ip)
                result = json.loads(b)
                from_node = worker + '@' + FLAGS.domain
                c = result[from_node]['cost']
                all_cost.append(float(c))
            # added cost of all slaves
            cost_i = sum(all_cost)

            ap = acceptance_probability(cost, cost_i, temp)
            rand = random.uniform(0, 1)
            if ap > rand:
                beta_car = new_beta_car
                beta_cost = new_beta_cost
                beta_tt = new_beta_tt
                cost = cost_i
                solutions.append(cost)
                betas_car.append(beta_car)
                betas_cost.append(beta_cost)
                betas_tt.append(beta_tt)
                print('results: ', beta_car, beta_cost, beta_tt, cost, initial_cost)
            i += 1
        temp = temp * alpha
        j += 1

    print(beta_car, beta_cost, beta_tt, cost, initial_cost, solutions, betas_car, betas_cost, betas_tt)

if __name__ == '__main__':
  app.run(main)