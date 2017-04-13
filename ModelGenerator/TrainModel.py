import datetime
import os
from time import time

import keras
import numpy as np
from keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau
from keras.preprocessing.image import ImageDataGenerator

from TrainingHistoryPlotter import TrainingHistoryPlotter
from datasets.MuscimaDataset import MuscimaDataset
from datasets.PascalVocDataset import PascalVocDataset
from models.ConfigurationFactory import ConfigurationFactory

print("Downloading and extracting datasets...")

dataset_directory = "data"

pascalVocDataset = PascalVocDataset(dataset_directory)
pascalVocDataset.download_and_extract_dataset()

muscimaDataset = MuscimaDataset(dataset_directory)
muscimaDataset.download_and_extract_dataset()

print("Training on datasets...")
start_time = time()

model_name = "simple"
training_configuration = ConfigurationFactory.get_configuration_by_name(model_name)
img_rows, img_cols = training_configuration.data_shape[0], training_configuration.data_shape[1]

train_generator = ImageDataGenerator(horizontal_flip=True)
training_data_generator = train_generator.flow_from_directory(os.path.join(dataset_directory, "training"),
                                                              target_size=(img_cols, img_rows),
                                                              batch_size=training_configuration.training_minibatch_size,
                                                              # save_to_dir="train_data"
                                                              )
training_steps_per_epoch = np.math.ceil(training_data_generator.samples / training_data_generator.batch_size)

validation_generator = ImageDataGenerator()
validation_data_generator = validation_generator.flow_from_directory(os.path.join(dataset_directory, "validation"),
                                                                     target_size=(img_cols, img_rows),
                                                                     batch_size=training_configuration.training_minibatch_size)
validation_steps_per_epoch = np.math.ceil(validation_data_generator.samples / validation_data_generator.batch_size)

model = training_configuration.classifier()
model.summary()

print("Model {0} loaded.".format(training_configuration.name()))
print(training_configuration.summary())

best_model_path = "{0}.h5".format(training_configuration.name())

model_checkpoint = ModelCheckpoint(best_model_path, monitor="val_acc", save_best_only=True, verbose=1)
early_stop = EarlyStopping(monitor='val_acc',
                           patience=training_configuration.number_of_epochs_before_early_stopping,
                           verbose=1)
learning_rate_reduction = ReduceLROnPlateau(monitor='val_acc',
                                            patience=training_configuration.number_of_epochs_before_reducing_learning_rate,
                                            verbose=1,
                                            factor=training_configuration.learning_rate_reduction_factor,
                                            min_lr=training_configuration.minimum_learning_rate)
history = model.fit_generator(
    generator=training_data_generator,
    steps_per_epoch=training_steps_per_epoch,
    epochs=training_configuration.number_of_epochs,
    callbacks=[model_checkpoint, early_stop, learning_rate_reduction],
    validation_data=validation_data_generator,
    validation_steps=validation_steps_per_epoch
)

print("Loading best model from check-point and testing...")
best_model = keras.models.load_model(best_model_path)

validation_data_generator.reset()
evaluation = best_model.evaluate_generator(validation_data_generator, steps=validation_steps_per_epoch)

print(best_model.metrics_names)
print("Loss : ", evaluation[0])
print("Accuracy : ", evaluation[1])
print("Error : ", 1 - evaluation[1])

TrainingHistoryPlotter.plot_history(history,
                                    "Results-{0}-{1}.png".format(training_configuration.name(), datetime.date.today()))

endTime = time()
print("Execution time: %.1fs" % (endTime - start_time))
