import json
import argparse
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
import tensorflow as tf
import keras
import keras_hub
import time
import os
import random

SEED = 42


def apply_seed(seed=SEED):
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    tf.random.set_seed(seed)
    try:
        tf.config.experimental.enable_op_determinism()
    except Exception:
        pass


# =====================================================================
# ARCHITECTURES (verbatim from samples/*.ipynb)
# =====================================================================

def arch_resnet18(num_classes):
    """ResNet18 - samples/ResNet18.ipynb (keras_hub ResNetBackbone imagenet)."""
    inputs = keras.Input(shape=(224, 224, 3))
    base_model = keras_hub.models.ResNetBackbone.from_preset(
        "resnet_18_imagenet", load_weights=True)
    base_model.trainable = True
    x = base_model(inputs)
    x = keras.layers.GlobalAveragePooling2D()(x)
    x = keras.layers.BatchNormalization()(x)
    x = keras.layers.Dense(1024, activation=None)(x)
    x = keras.layers.Dropout(0.3)(x)
    outputs = keras.layers.Dense(num_classes, activation="softmax")(x)
    return keras.Model(inputs, outputs)


def arch_resnet50(num_classes):
    """ResNet50 - samples/JnJ_CNN.ipynb (Architecture 1)."""
    inputs = tf.keras.Input(shape=(224, 224, 3))
    x = tf.keras.applications.resnet50.preprocess_input(inputs)
    base_model = tf.keras.applications.ResNet50(
        weights="imagenet", include_top=False, input_tensor=x)
    base_model.trainable = True
    x = base_model.output
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Dense(1024, activation=None)(x)
    x = tf.keras.layers.Dropout(0.3)(x)
    outputs = tf.keras.layers.Dense(num_classes, activation="softmax")(x)
    return tf.keras.Model(inputs, outputs)


def inception_block(inputs, filters, name=None):
    """GoogLeNet-style Inception block (FMD arch 1)."""
    branch1 = tf.keras.layers.Conv2D(
        filters=filters["branch1"], kernel_size=(1, 1), padding="same",
        activation="relu", name=f"{name}_branch1_1x1")(inputs)

    branch2 = tf.keras.layers.Conv2D(
        filters=filters["branch2_reduce"], kernel_size=(1, 1), padding="same",
        activation="relu", name=f"{name}_branch2_reduce")(inputs)
    branch2 = tf.keras.layers.Conv2D(
        filters=filters["branch2_out"], kernel_size=(3, 3), padding="same",
        activation="relu", name=f"{name}_branch2_3x3")(branch2)

    branch3 = tf.keras.layers.Conv2D(
        filters=filters["branch3_reduce"], kernel_size=(1, 1), padding="same",
        activation="relu", name=f"{name}_branch3_reduce")(inputs)
    branch3 = tf.keras.layers.Conv2D(
        filters=filters["branch3_out"], kernel_size=(5, 5), padding="same",
        activation="relu", name=f"{name}_branch3_5x5")(branch3)

    branch4 = tf.keras.layers.MaxPooling2D(
        pool_size=(3, 3), strides=(1, 1), padding="same",
        name=f"{name}_branch4_pool")(inputs)
    branch4 = tf.keras.layers.Conv2D(
        filters=filters["branch4_out"], kernel_size=(1, 1), padding="same",
        activation="relu", name=f"{name}_branch4_1x1")(branch4)

    return tf.keras.layers.Concatenate(axis=-1, name=f"{name}_concat")(
        [branch1, branch2, branch3, branch4])


def arch_resnet50_inception(num_classes):
    """ResNet50 MultiLevel MultiScale (FMD arch 1)."""
    inputs = tf.keras.Input(shape=(224, 224, 3))
    x = tf.keras.applications.resnet50.preprocess_input(inputs)
    base_model = tf.keras.applications.ResNet50(
        weights="imagenet", include_top=False, input_tensor=x)
    base_model.trainable = True

    l3 = base_model.get_layer("conv3_block4_add").output   # 28x28x512
    l4 = base_model.get_layer("conv4_block6_add").output   # 14x14x1024
    l5 = base_model.get_layer("conv5_block3_add").output   # 7x7x2048

    l3_filters = {"branch1": 64, "branch2_reduce": 96, "branch2_out": 104,
                  "branch3_reduce": 32, "branch3_out": 172, "branch4_out": 172}
    l4_filters = {"branch1": 128, "branch2_reduce": 192, "branch2_out": 208,
                  "branch3_reduce": 64, "branch3_out": 344, "branch4_out": 344}
    l5_filters = {"branch1": 256, "branch2_reduce": 384, "branch2_out": 416,
                  "branch3_reduce": 128, "branch3_out": 688, "branch4_out": 688}

    i3 = inception_block(l3, filters=l3_filters, name="inception_l3")
    i4 = inception_block(l4, filters=l4_filters, name="inception_l4")
    i5 = inception_block(l5, filters=l5_filters, name="inception_l5")

    x3 = tf.keras.layers.LeakyReLU(negative_slope=0.1)(i3)
    x3 = tf.keras.layers.MaxPooling2D(pool_size=(2, 2))(x3)

    x4 = i4

    x5 = tf.keras.layers.LeakyReLU(negative_slope=0.1)(i5)
    x5 = tf.keras.layers.Conv2DTranspose(
        filters=2048, kernel_size=(2, 2), strides=(2, 2), padding="same")(x5)
    x5 = tf.keras.layers.BatchNormalization()(x5)
    x5 = tf.keras.layers.LeakyReLU(negative_slope=0.1)(x5)

    fusion = tf.keras.layers.Concatenate(axis=-1)([x3, x4, x5])

    x = tf.keras.layers.GlobalAveragePooling2D()(fusion)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Dense(2048, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.3)(x)
    x = tf.keras.layers.Dense(1024, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.3)(x)
    outputs = tf.keras.layers.Dense(num_classes, activation="softmax")(x)
    return tf.keras.Model(inputs, outputs)


def se_block(inputs, reduction=16, name=None):
    """Squeeze-and-Excitation block (FMD arch 2)."""
    channels = int(inputs.shape[-1])
    x = tf.keras.layers.GlobalAveragePooling2D(
        name=f"{name}_gap" if name else None)(inputs)
    x = tf.keras.layers.Dense(
        channels // reduction, activation="relu", use_bias=True,
        name=f"{name}_fc1" if name else None)(x)
    x = tf.keras.layers.Dense(
        channels, activation="sigmoid", use_bias=True,
        name=f"{name}_fc2" if name else None)(x)
    x = tf.keras.layers.Reshape(
        (1, 1, channels), name=f"{name}_reshape" if name else None)(x)
    return tf.keras.layers.Multiply(
        name=f"{name}_scale" if name else None)([inputs, x])


def arch_resnet50_se(num_classes):
    """ResNet50 MultiLevel Attention (FMD arch 2)."""
    inputs = tf.keras.Input(shape=(224, 224, 3))
    x = tf.keras.applications.resnet50.preprocess_input(inputs)
    base_model = tf.keras.applications.ResNet50(
        weights="imagenet", include_top=False, input_tensor=x)
    base_model.trainable = True

    l3 = base_model.get_layer("conv3_block4_add").output   # 28x28x512
    l4 = base_model.get_layer("conv4_block6_add").output   # 14x14x1024
    l5 = base_model.get_layer("conv5_block3_add").output   # 7x7x2048

    l3_se = se_block(l3, reduction=16, name="se3")
    l4_se = se_block(l4, reduction=16, name="se4")
    l5_se = se_block(l5, reduction=16, name="se5")

    x3 = tf.keras.layers.LeakyReLU(negative_slope=0.1)(l3_se)
    x3 = tf.keras.layers.MaxPooling2D(pool_size=(2, 2))(x3)

    x4 = l4_se

    x5 = tf.keras.layers.LeakyReLU(negative_slope=0.1)(l5_se)
    x5 = tf.keras.layers.Conv2DTranspose(
        filters=2048, kernel_size=(2, 2), strides=(2, 2), padding="same")(x5)
    x5 = tf.keras.layers.BatchNormalization()(x5)
    x5 = tf.keras.layers.LeakyReLU(negative_slope=0.1)(x5)

    fusion = tf.keras.layers.Concatenate(axis=-1)([x3, x4, x5])

    x = tf.keras.layers.GlobalAveragePooling2D()(fusion)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Dense(2048, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.3)(x)
    x = tf.keras.layers.Dense(1024, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.3)(x)
    outputs = tf.keras.layers.Dense(num_classes, activation="softmax")(x)
    return tf.keras.Model(inputs, outputs)


def inception_attention_block(inputs, filters, name=None):
    """GoogLeNet-style Inception block with Squeeze-and-Excitation attention on
    every branch (FMD arch 3). The four branches are the same as
    inception_block; each branch output is passed through se_block(reduction=16).
    Spatial dimensions are preserved.
    """
    # Branch 1: 1x1
    branch1 = tf.keras.layers.Conv2D(
        filters=filters["branch1"], kernel_size=(1, 1), padding="same",
        activation="relu", name=f"{name}_branch1_1x1")(inputs)
    branch1 = se_block(branch1, reduction=16, name=f"{name}_branch1_se")

    # Branch 2: 1x1 -> 3x3
    branch2 = tf.keras.layers.Conv2D(
        filters=filters["branch2_reduce"], kernel_size=(1, 1), padding="same",
        activation="relu", name=f"{name}_branch2_reduce")(inputs)
    branch2 = tf.keras.layers.Conv2D(
        filters=filters["branch2_out"], kernel_size=(3, 3), padding="same",
        activation="relu", name=f"{name}_branch2_3x3")(branch2)
    branch2 = se_block(branch2, reduction=16, name=f"{name}_branch2_se")

    # Branch 3: 1x1 -> 5x5
    branch3 = tf.keras.layers.Conv2D(
        filters=filters["branch3_reduce"], kernel_size=(1, 1), padding="same",
        activation="relu", name=f"{name}_branch3_reduce")(inputs)
    branch3 = tf.keras.layers.Conv2D(
        filters=filters["branch3_out"], kernel_size=(5, 5), padding="same",
        activation="relu", name=f"{name}_branch3_5x5")(branch3)
    branch3 = se_block(branch3, reduction=16, name=f"{name}_branch3_se")

    # Branch 4: 3x3 MaxPool -> 1x1
    branch4 = tf.keras.layers.MaxPooling2D(
        pool_size=(3, 3), strides=(1, 1), padding="same",
        name=f"{name}_branch4_pool")(inputs)
    branch4 = tf.keras.layers.Conv2D(
        filters=filters["branch4_out"], kernel_size=(1, 1), padding="same",
        activation="relu", name=f"{name}_branch4_1x1")(branch4)
    branch4 = se_block(branch4, reduction=16, name=f"{name}_branch4_se")

    return tf.keras.layers.Concatenate(
        axis=-1, name=f"{name}_concat")([branch1, branch2, branch3, branch4])


def arch_resnet50_inception_attention(num_classes):
    """ResNet50 MultiLevel Inception with branch attention (FMD arch 3:
    "ResNet50 Architecture MultiLevel Attention" in FMD_ResNet50Architectures).
    Same Inception fusion as arch 1, with SE attention inside every branch."""
    inputs = tf.keras.Input(shape=(224, 224, 3))
    x = tf.keras.applications.resnet50.preprocess_input(inputs)
    base_model = tf.keras.applications.ResNet50(
        weights="imagenet", include_top=False, input_tensor=x)
    base_model.trainable = True

    l3 = base_model.get_layer("conv3_block4_add").output   # 28x28x512
    l4 = base_model.get_layer("conv4_block6_add").output   # 14x14x1024
    l5 = base_model.get_layer("conv5_block3_add").output   # 7x7x2048

    l3_filters = {
        "branch1": 64,
        "branch2_reduce": 96,
        "branch2_out": 104,
        "branch3_reduce": 32,
        "branch3_out": 172,
        "branch4_out": 172,
    }
    l4_filters = {
        "branch1": 128,
        "branch2_reduce": 192,
        "branch2_out": 208,
        "branch3_reduce": 64,
        "branch3_out": 344,
        "branch4_out": 344,
    }
    l5_filters = {
        "branch1": 256,
        "branch2_reduce": 384,
        "branch2_out": 416,
        "branch3_reduce": 128,
        "branch3_out": 688,
        "branch4_out": 688,
    }

    i3 = inception_attention_block(
        l3, filters=l3_filters, name="inception_att_l3")     # 28x28x512
    i4 = inception_attention_block(
        l4, filters=l4_filters, name="inception_att_l4")     # 14x14x1024
    i5 = inception_attention_block(
        l5, filters=l5_filters, name="inception_att_l5")     # 7x7x2048

    x3 = tf.keras.layers.LeakyReLU(negative_slope=0.1)(i3)
    x3 = tf.keras.layers.MaxPooling2D(pool_size=(2, 2))(x3)

    x4 = i4

    x5 = tf.keras.layers.LeakyReLU(negative_slope=0.1)(i5)
    x5 = tf.keras.layers.Conv2DTranspose(
        filters=2048, kernel_size=(2, 2), strides=(2, 2), padding="same")(x5)
    x5 = tf.keras.layers.BatchNormalization()(x5)
    x5 = tf.keras.layers.LeakyReLU(negative_slope=0.1)(x5)

    fusion = tf.keras.layers.Concatenate(axis=-1)([x3, x4, x5])

    x = tf.keras.layers.GlobalAveragePooling2D()(fusion)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Dense(2048, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.3)(x)
    x = tf.keras.layers.Dense(1024, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.3)(x)
    outputs = tf.keras.layers.Dense(num_classes, activation="softmax")(x)
    return tf.keras.Model(inputs, outputs)


def arch_resnet50_inception_refine(num_classes):
    """ResNet50 MultiLevel Inception with a refined decoded L5 path (FMD arch 4:
    the last cell of FMD_ResNet50Architectures). Same Inception fusion as arch 1,
    but the 7x7x2048 L5 feature is decoded with bicubic upsampling plus a
    depthwise spatial refinement and a 1x1 channel mixer instead of a
    transposed convolution."""
    inputs = tf.keras.Input(shape=(224, 224, 3))
    x = tf.keras.applications.resnet50.preprocess_input(inputs)
    base_model = tf.keras.applications.ResNet50(
        weights="imagenet", include_top=False, input_tensor=x)
    base_model.trainable = True

    l3 = base_model.get_layer("conv3_block4_add").output   # 28x28x512
    l4 = base_model.get_layer("conv4_block6_add").output   # 14x14x1024
    l5 = base_model.get_layer("conv5_block3_add").output   # 7x7x2048

    l3_filters = {
        "branch1": 64,
        "branch2_reduce": 96,
        "branch2_out": 104,
        "branch3_reduce": 32,
        "branch3_out": 172,
        "branch4_out": 172,
    }
    l4_filters = {
        "branch1": 128,
        "branch2_reduce": 192,
        "branch2_out": 208,
        "branch3_reduce": 64,
        "branch3_out": 344,
        "branch4_out": 344,
    }
    l5_filters = {
        "branch1": 256,
        "branch2_reduce": 384,
        "branch2_out": 416,
        "branch3_reduce": 128,
        "branch3_out": 688,
        "branch4_out": 688,
    }

    i3 = inception_block(l3, filters=l3_filters, name="inception_l3")
    i4 = inception_block(l4, filters=l4_filters, name="inception_l4")
    i5 = inception_block(l5, filters=l5_filters, name="inception_l5")

    x3 = tf.keras.layers.LeakyReLU(negative_slope=0.1)(i3)
    x3 = tf.keras.layers.MaxPooling2D(pool_size=(2, 2))(x3)

    x4 = i4

    # 7x7x2048 -> 14x14x2048 by bicubic upsample, then spatial refinement
    x5 = tf.keras.layers.LeakyReLU(negative_slope=0.1)(i5)

    x5 = tf.keras.layers.UpSampling2D(
        size=(2, 2), interpolation="bicubic")(x5)

    x5 = tf.keras.layers.DepthwiseConv2D(
        kernel_size=(3, 3), padding="same", use_bias=False)(x5)
    x5 = tf.keras.layers.BatchNormalization()(x5)
    x5 = tf.keras.layers.LeakyReLU(negative_slope=0.1)(x5)

    x5 = tf.keras.layers.Conv2D(
        filters=2048, kernel_size=(1, 1), padding="same", use_bias=False)(x5)
    x5 = tf.keras.layers.BatchNormalization()(x5)
    x5 = tf.keras.layers.LeakyReLU(negative_slope=0.1)(x5)

    fusion = tf.keras.layers.Concatenate(axis=-1)([x3, x4, x5])

    x = tf.keras.layers.GlobalAveragePooling2D()(fusion)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Dense(2048, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.3)(x)
    x = tf.keras.layers.Dense(1024, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.3)(x)
    outputs = tf.keras.layers.Dense(num_classes, activation="softmax")(x)
    return tf.keras.Model(inputs, outputs)


ARCH_BUILDERS = {
    "resnet18": arch_resnet18,
    "resnet50": arch_resnet50,
    "resnet50_inception": arch_resnet50_inception,
    "resnet50_se": arch_resnet50_se,
    "resnet50_inception_attention": arch_resnet50_inception_attention,
    "resnet50_inception_refine": arch_resnet50_inception_refine,
}

# Reader-facing names, so a results file says which architecture it is in the words the
# table and the lead use, not only in the key.
ARCH_LABELS = {
    "resnet18": "ResNet18",
    "resnet50": "ResNet50 (Architecture 1 baseline)",
    "resnet50_inception": "ResNet50-Inception MultiLevel MultiScale (Architecture 1, multi-scale)",
    "resnet50_se": "ResNet50-SE (channel attention)",
    "resnet50_inception_attention": "ResNet50-Inception-SE (branch attention, Architecture 3)",
    "resnet50_inception_refine": "ResNet50-Inception-Refine (Architecture 4)",
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="FMD Lens Presentation classifier - 6 architectures.")
    ap.add_argument("--arch", required=True,
                    choices=sorted(ARCH_BUILDERS),
                    help="which architecture to train")
    ap.add_argument("--data", required=True,
                    help="dataset root containing train/ and test/ subdirs")
    ap.add_argument("--epochs", type=int, required=True)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--warmup", action="store_true",
                    help="run warmup predict pass before timing inference")
    args = ap.parse_args(argv)
    apply_seed(args.seed)
    os.makedirs(args.outdir, exist_ok=True)

    train_ds = tf.keras.utils.image_dataset_from_directory(
        f"{args.data}/train",
        image_size=(224, 224),
        batch_size=args.batch_size,
        shuffle=True,
        seed=args.seed,
    )
    test_ds = tf.keras.utils.image_dataset_from_directory(
        f"{args.data}/test",
        image_size=(224, 224),
        batch_size=args.batch_size,
        shuffle=False,
    )

    class_names = train_ds.class_names
    num_classes = len(class_names)
    tf.keras.utils.set_random_seed(args.seed)

    model = ARCH_BUILDERS[args.arch](num_classes)

    optimizer = tf.keras.optimizers.SGD(
        learning_rate=1e-4,
        momentum=0.9,
        nesterov=True
    )
    model.compile(
        optimizer=optimizer,
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"]
    )

    start_time = time.perf_counter()
    history = model.fit(train_ds, epochs=args.epochs)
    end_time = time.perf_counter()
    training_time = end_time - start_time
    print(f"Total Training Time : {training_time:.2f} seconds")

    # Collect true labels
    y_true = np.concatenate(
        [labels.numpy() for _, labels in test_ds], axis=0)
    num_test_images = sum(images.shape[0] for images, _ in test_ds)


    # Warmup: warm BOTH the model and the real file-based test pipeline.
    # A dummy-data pass warms the XLA graph + cuDNN autotune, but model.predict()
    # re-traces a new graph the first time it is fed the real
    # image_dataset_from_directory pipeline. On the A100 that is an ~1.1 s
    # one-time cost that, when left inside the timed inference, inflates
    # ms/img and exaggerates the difference between test sets of different size
    # (87 vs 201 images). Discard one real-pipeline predict to absorb it.
    if args.warmup:
        _warmup_ds = tf.data.Dataset.from_tensor_slices(
            (tf.random.normal((64, 224, 224, 3)), tf.zeros((64,), dtype=tf.int32))
        ).batch(args.batch_size)
        _ = model.predict(_warmup_ds, verbose=0)
        _ = model.predict(_warmup_ds, verbose=0)
        _ = model.predict(test_ds, verbose=0)   # warm the real test pipeline (discarded)
        print("Warmup complete (2 dummy passes + 1 real-pipeline pass)")


    start = time.perf_counter()
    y_pred_prob = model.predict(test_ds, verbose=1)
    end = time.perf_counter()
    y_pred = np.argmax(y_pred_prob, axis=1)

    accuracy = accuracy_score(y_true, y_pred)
    print(f"Overall Accuracy : {accuracy*100:.2f}%")
    total_time = end - start
    time_per_image = total_time / num_test_images
    print(f"Total inference time : {total_time:.4f} sec")
    print(f"Images               : {num_test_images}")
    print(f"Inference/image      : {time_per_image*1000:.3f} ms")

    # Confusion Matrix
    cm = confusion_matrix(y_true, y_pred)
    class_accuracy = cm.diagonal() / cm.sum(axis=1)
    print("\nClass-wise Accuracy (Recall):\n")
    for cls, acc in zip(class_names, class_accuracy):
        print(f"{cls}: {acc*100:.2f}%")

    # Precision / Recall / F1 (per-class + macro + weighted)
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=list(range(num_classes)), zero_division=0)
    print("\nPer-class precision / recall / f1:")
    for cls, p, r, f, s in zip(class_names, precision, recall, f1, support):
        print(f"  {cls}: prec={p*100:.2f}%  rec={r*100:.2f}%  f1={f*100:.2f}%  n={int(s)}")
    macro_p, weighted_p = precision.mean(), np.average(precision, weights=support)
    macro_r, weighted_r = recall.mean(), np.average(recall, weights=support)
    macro_f1, weighted_f1 = f1.mean(), np.average(f1, weights=support)
    print(f"\nMacro    precision={(macro_p*100):.2f}%  recall={(macro_r*100):.2f}%  f1={(macro_f1*100):.2f}%")
    # ---------------------------------------------------------------
    # Persist all metrics for this run (read by the results landing pad)
    # ---------------------------------------------------------------
    train_path = f"{args.data}/train"
    num_train_images = sum(
        len(os.listdir(os.path.join(train_path, cname)))
        for cname in class_names)
    run_metrics = {
        "arch": args.arch,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "seed": args.seed,
        "num_classes": num_classes,
        "class_names": class_names,
        "num_train_images": num_train_images,
        "num_test_images": num_test_images,
        "overall_accuracy": round(float(accuracy), 4),
        "overall_recall": round(float(np.mean(class_accuracy)), 4),
        "training_time_sec": round(training_time, 2),
        "inference_total_sec": round(float(total_time), 4),
        "inference_per_image_ms": round(float(time_per_image * 1000), 3),
        "per_class": {
            cls: {
                "recall": round(float(r), 4),
                "precision": round(float(p), 4),
                "f1": round(float(f), 4),
                "support": int(s),
            }
            for cls, p, r, f, s
            in zip(class_names, precision, recall, f1, support)
        },
        "macro": {
            "precision": round(float(macro_p), 4),
            "recall": round(float(macro_r), 4),
            "f1": round(float(macro_f1), 4),
        },
        "weighted": {
            "precision": round(float(weighted_p), 4),
            "recall": round(float(weighted_r), 4),
            "f1": round(float(weighted_f1), 4),
        },
    }
    mjson = os.path.join(args.outdir, "metrics.json")
    with open(mjson, "w") as fh:
        json.dump(run_metrics, fh, indent=2)
    print(f"Saved metrics: {mjson}")

    # Plot confusion matrix

    fig, ax = plt.subplots(figsize=(10, 10))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm,
                                  display_labels=class_names)
    disp.plot(cmap="Blues", xticks_rotation=90, ax=ax, colorbar=False)
    plt.title(f"Confusion Matrix - {args.arch}")
    plt.tight_layout()
    png = os.path.join(args.outdir, f"confusion_matrix_{args.arch}.png")
    plt.savefig(png, dpi=300, bbox_inches="tight")
    print(f"\nSaved confusion matrix: {png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
