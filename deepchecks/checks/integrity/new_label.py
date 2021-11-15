"""The data_sample_leakage_report check module."""

from deepchecks import Dataset
from deepchecks.base.check import CheckResult, TrainValidationBaseCheck
from deepchecks.string_utils import format_percent

import pandas as pd

pd.options.mode.chained_assignment = None

__all__ = ['NewLabelTrainValidation']


class NewLabelTrainValidation(TrainValidationBaseCheck):
    """Find new labels in validation."""

    def run(self, train_dataset: Dataset, validation_dataset: Dataset, model=None) -> CheckResult:
        """Run check.

        Args:
            train_dataset (Dataset): The training dataset object.
            validation_dataset (Dataset): The validation dataset object.
            model: any = None - not used in the check
        Returns:
            CheckResult: value is a dictionary that shows label column with new labels
                         displays a dataframe that label columns with new labels
        Raises:
            DeepchecksValueError: If the datasets are not a Dataset instance or do not contain label column
        """
        return self._new_label_train_validation(train_dataset=train_dataset,
                                                validation_dataset=validation_dataset)

    def _new_label_train_validation(self, train_dataset: Dataset, validation_dataset: Dataset):
        validation_dataset = Dataset.validate_dataset_or_dataframe(validation_dataset)
        train_dataset = Dataset.validate_dataset_or_dataframe(train_dataset)
        validation_dataset.validate_label(self.__class__.__name__)
        train_dataset.validate_label(self.__class__.__name__)
        validation_dataset.validate_shared_label(train_dataset, self.__class__.__name__)

        label_column = train_dataset.validate_shared_label(validation_dataset, self.__class__.__name__)

        n_validation_samples = validation_dataset.n_samples()

        train_label = train_dataset.data[label_column]
        validation_label = validation_dataset.data[label_column]

        unique_training_values = set(train_label.unique())
        unique_validation_values = set(validation_label.unique())

        new_labels = unique_validation_values.difference(unique_training_values)

        if new_labels:
            n_new_label = len(validation_label[validation_label.isin(new_labels)])

            dataframe = pd.DataFrame(data=[[label_column, format_percent(n_new_label / n_validation_samples),
                                            sorted(new_labels)]],
                                     columns=['Label column', 'Percent new labels in sample', 'New labels'])
            dataframe = dataframe.set_index(['Label column'])

            display = dataframe

            result = {label_column: n_new_label / n_validation_samples}
        else:
            display = None
            result = {}

        return CheckResult(result, check=self.run, display=display)