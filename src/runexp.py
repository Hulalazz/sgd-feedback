import json
import pickle
from argparse import ArgumentParser

import numpy as np
from keras.datasets import mnist, cifar10, cifar100
from keras.utils import np_utils

from gridopts import *
from models import *
from dna import DNAMonitor


def pre_process_image(args):
    (X_train, y_train), _ = DATASET_INFO[args.dataset]["loader"]()
    if args.n_samples is not None:
        X_train, y_train = X_train[:args.n_samples], y_train[:args.n_samples]
    X_train = X_train.astype("float32") / 255.
    if X_train.ndim == 3:
        X_train = X_train[:, np.newaxis, :, :]
    if args.flatten:
        X_train = X_train.reshape((X_train.shape[0], -1))
    y_train = np_utils.to_categorical(y_train, DATASET_INFO[args.dataset]["nb_classes"])
    return X_train, y_train


DATASET_INFO = {
    "mnist": {"loader": mnist.load_data, "nb_classes": 10, "preprocess": pre_process_image},
    "cifar10": {"loader": cifar10.load_data, "nb_classes": 10, "preprocess": pre_process_image},
    "cifar100": {"loader": cifar100.load_data, "nb_classes": 100, "preprocess": pre_process_image}
}


arg_parser = ArgumentParser()
arg_parser.add_argument("--optimizer", type=str, required=True, choices=OPTIMIZERS_INDEX.keys())
arg_parser.add_argument("--opt-args", type=json.loads, required=True)
arg_parser.add_argument("--model", type=str, required=True, choices=MODEL_FACTORIES.keys())
arg_parser.add_argument("--dataset", type=str, required=True, choices=DATASET_INFO.keys())
arg_parser.add_argument("--batch-size", type=int, required=True)
arg_parser.add_argument("--epochs", type=int, required=True)
arg_parser.add_argument("--save-path", type=str, required=True)
arg_parser.add_argument("--n-samples", type=int, default=None)
arg_parser.add_argument("--flatten", action="store_true")
args = arg_parser.parse_args()

grid_opt = OPTIMIZERS_INDEX[args.optimizer](**args.opt_args)

X_train, y_train = DATASET_INFO[args.dataset]["preprocess"](args)

best_final_loss = np.inf
for opt in grid_opt:
    model = MODEL_FACTORIES[args.model](X_train.shape[1:], DATASET_INFO[args.dataset]["nb_classes"])
    model.compile(optimizer=opt, loss="categorical_crossentropy", metrics=["accuracy"])
    if args.optimizer == "dna":
        dna_monitor = DNAMonitor()
        callbacks = [dna_monitor]
    else:
        callbacks = []
    history = model.fit(x=X_train, y=y_train, batch_size=args.batch_size, nb_epoch=args.epochs, verbose=1, callbacks=callbacks)

    if history.history["loss"][-1] < best_final_loss:
        best_final_loss = history.history["loss"][-1]
        best_loss_history = history.history["loss"]
        best_opt_config = opt.get_config()
        best_decay = opt.decay.get_value()
        if args.optimizer == "dna":
            best_dna_monitor = dna_monitor

save_data = {
    "best_loss_history": best_loss_history,
    "param_grid": grid_opt.grid,
    "best_opt_config": best_opt_config,
    "best_decay": best_decay,
    "cmd_args": args,
}
if args.optimizer == "dna":
    save_data["best_batch_loss_history"] = best_dna_monitor.batch_losses
    save_data["ds"] = best_dna_monitor.ds
with open(args.save_path, "wb") as f:
    pickle.dump(save_data, f)

