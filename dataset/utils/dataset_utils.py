import os
import ujson
import numpy as np
import gc
from sklearn.model_selection import train_test_split

batch_size = 16
train_size = 0.75
least_samples = batch_size / (1-train_size)

def check(config_path, train_path, test_path, num_clients, num_labels, niid=False, real=True):
    # check existing dataset
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = ujson.load(f)
        if config['num_clients'] == num_clients and \
            config['num_labels'] == num_labels and \
            config['non_iid'] == niid and \
            config['real_world'] == real:
            print("\nDataset already generated.\n")
            return True

    dir_path = os.path.dirname(train_path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    dir_path = os.path.dirname(test_path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    return False

def seperete_data(data, num_clients, num_labels, niid=False, real=True, class_per_client=2):
    print("\nOriginal number of samples of each label: ", [len(v) for v in data])
    print()

    X = [[] for _ in range(num_clients)]
    y = [[] for _ in range(num_clients)]
    statistic = [[] for _ in range(num_clients)]
    if not niid or real:
        class_per_client = num_labels
    class_num_client = [class_per_client for _ in range(num_clients)]
    for i in range(num_labels):
        selected_clients = []
        for client in range(num_clients):
            if class_num_client[client] > 0:
                selected_clients.append(client)
        if niid and not real:
            selected_clients = selected_clients[:int(num_clients/num_labels*class_per_client)]

        num_all = len(data[i])
        num_clients_ = len(selected_clients)
        if niid and real:
            num_clients_ = np.random.randint(1, len(selected_clients))
        num_per = num_all / num_clients_
        num_samples = np.random.randint(max(num_per/10, least_samples), num_per, num_clients_-1).tolist()
        num_samples.append(num_all-sum(num_samples))
        idx = 0
        
        
        if niid:
            # each client is not sure to have all the labels
            selected_clients = list(np.random.choice(selected_clients, num_clients_, replace=False))

        for client, num_sample in zip(selected_clients, num_samples): 
            X[client] += data[i][idx:idx+num_sample].tolist()
            y[client] += (i*np.ones(num_sample)).tolist()
            idx += num_sample
            statistic[client].append((i, num_sample))
            class_num_client[client] -= 1

    del data
    gc.collect()

    for client in range(num_clients):
        print(f"Client {client}\t Size of data: {len(X[client])}\t Labels: ", np.unique(y[client]))
        print(f"Client {client}\t Samples of labels: ", [i for i in statistic[client]])
        print("-" * 50)

    return X, y, statistic

def split_data(X, y, num_clients, train_size=train_size):
    # Split dataset
    train_data = {'clients': [], 'client_data': {}, 'num_samples': []}
    test_data = {'clients': [], 'client_data': {}, 'num_samples': []}

    for i in range(num_clients):
        uname = 'f_{0:05d}'.format(i)

        unique, count = np.unique(y[i], return_counts=True)
        if min(count) > 1:
            X_train, X_test, y_train, y_test = train_test_split(
                X[i], y[i], train_size=train_size, shuffle=True, stratify=y[i])
        else:
            X_train, X_test, y_train, y_test = train_test_split(
                X[i], y[i], train_size=train_size, shuffle=True, stratify=None)

        train_data["client_data"][uname] = {'x': X_train, 'y': y_train}
        train_data['clients'].append(uname)
        train_data['num_samples'].append(len(y_train))
        test_data['clients'].append(uname)
        test_data["client_data"][uname] = {'x': X_test, 'y': y_test}
        test_data['num_samples'].append(len(y_test))

    print("Total number of samples:", sum(train_data['num_samples'] + test_data['num_samples']))
    print("The number of train samples:", train_data['num_samples'])
    print("The number of test samples:", test_data['num_samples'])
    print()
    del X, y
    gc.collect()

    return train_data, test_data

def save_file(config_path, train_path, test_path, train_data, test_data, num_clients, num_labels, statistic, niid=False, real=True):
    config = {
        'num_clients': num_clients, 
        'num_labels': num_labels, 
        'non_iid': niid, 
        'real_world': real, 
    }
    config.update({
        'train_samples_of_each_label': train_data['num_samples'], 
        'test_samples_of_each_label': test_data['num_samples'], 
        'total_samples': sum(train_data['num_samples'] + test_data['num_samples']),
        'Size of samples for labels in clients': statistic, 
    })

    gc.collect()

    with open(train_path, 'w') as f:
        ujson.dump(train_data, f)
    with open(test_path, 'w') as f:
        ujson.dump(test_data, f)
    with open(config_path, 'w') as f:
        ujson.dump(config, f)

    print("Finish generating dataset.\n")