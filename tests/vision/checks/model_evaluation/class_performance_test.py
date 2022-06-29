# ----------------------------------------------------------------------------
# Copyright (C) 2021 Deepchecks (https://www.deepchecks.com)
#
# This file is part of Deepchecks.
# Deepchecks is distributed under the terms of the GNU Affero General
# Public License (version 3 or later).
# You should have received a copy of the GNU Affero General Public License
# along with Deepchecks.  If not, see <http://www.gnu.org/licenses/>.
# ----------------------------------------------------------------------------
#
import re
import typing as t

from hamcrest import (all_of, assert_that, calling, close_to, contains_exactly, contains_string, equal_to, greater_than,
                      has_items, has_length, has_property, instance_of, is_, is_in, raises)
from ignite.metrics import Precision, Recall
from plotly.basedatatypes import BaseFigure

from deepchecks.core.errors import DeepchecksValueError
from deepchecks.vision.checks import ClassPerformance
from tests.base.utils import equal_condition_result
from tests.common import assert_class_performance_display


def test_mnist_average_error_error(mnist_dataset_train, mnist_dataset_test, mock_trained_mnist, device):
    # Arrange
    check = ClassPerformance(alternative_metrics={'p': Precision(average=True)})
    # Act
    assert_that(
        calling(check.run
                ).with_args(mnist_dataset_train, mnist_dataset_test, mock_trained_mnist,
                            device=device),
        raises(DeepchecksValueError,
               r'The metric p returned a <class \'float\'> instead of an array/tensor')
    )


def test_mnist_largest(mnist_dataset_train, mnist_dataset_test, mock_trained_mnist, device):
    # Arrange
    check = ClassPerformance(n_to_show=2, show_only='largest')

    # Act
    result = check.run(mnist_dataset_train, mnist_dataset_test, mock_trained_mnist,
                       device=device, n_samples=None)

    # Assert
    assert_that(set(result.value['Class']), has_length(10))
    assert_that(result.value, has_length(40))
    assert_that(result.display, has_length(1))

    figure = t.cast(BaseFigure, result.display[0])
    assert_that(figure, instance_of(BaseFigure))

    assert_that(figure.data, assert_class_performance_display(
        xaxis=[
            contains_exactly(equal_to('2'), equal_to('1')),
            contains_exactly(equal_to('1'), equal_to('2')),
            contains_exactly(equal_to('2'), equal_to('1')),
            contains_exactly(equal_to('2'), equal_to('1')),
        ],
        yaxis=[
            contains_exactly(
                close_to(0.984, 0.001),
                close_to(0.977, 0.001),
            ),
            contains_exactly(
                close_to(0.974, 0.001),
                close_to(0.973, 0.001),
            ),
            contains_exactly(
                close_to(0.988, 0.001),
                close_to(0.987, 0.001),
            ),
            contains_exactly(
                close_to(0.984, 0.001),
                close_to(0.980, 0.001),
            )
        ]
    ))


def test_mnist_largest_without_display(mnist_dataset_train, mnist_dataset_test, mock_trained_mnist, device):
    # Arrange
    check = ClassPerformance(n_to_show=2, show_only='largest')
    # Act
    result = check.run(mnist_dataset_train, mnist_dataset_test, mock_trained_mnist,
                       device=device, n_samples=None, with_display=False)

    # Assert
    assert_that(set(result.value['Class']), has_length(10))
    assert_that(result.value, has_length(40))
    assert_that(result.display, has_length(0))


def test_mnist_smallest(mnist_dataset_train, mnist_dataset_test, mock_trained_mnist, device):
    # Arrange

    check = ClassPerformance(n_to_show=2, show_only='smallest')
    # Act
    result = check.run(mnist_dataset_train, mnist_dataset_test, mock_trained_mnist,
                       device=device)

    # Assert
    assert_that(result.value, has_length(40))
    assert_that(result.display, has_length(greater_than(0)))

    figure = t.cast(BaseFigure, result.display[0])
    assert_that(figure, instance_of(BaseFigure))

    assert_that(figure.data, assert_class_performance_display(
        metrics=('Precision', 'Recall'),
        xaxis=[
            contains_exactly(equal_to('6'), equal_to('5')),
            contains_exactly(equal_to('6'), equal_to('5')),
            contains_exactly(equal_to('6'), equal_to('5')),
            contains_exactly(equal_to('6'), equal_to('5')),
        ],
        yaxis=[
            contains_exactly(
                close_to(0.992, 0.001),
                close_to(0.983, 0.001),
            ),
            contains_exactly(
                close_to(0.981, 0.001),
                close_to(0.979, 0.001),
            ),
            contains_exactly(
                close_to(0.989, 0.001),
                close_to(0.975, 0.001),
            ),
            contains_exactly(
                close_to(0.984, 0.001),
                close_to(0.976, 0.001),
            )
        ]
    ))


def test_mnist_worst(mnist_dataset_train, mnist_dataset_test, mock_trained_mnist, device):
    # Arrange

    check = ClassPerformance(n_to_show=2, show_only='worst')
    # Act
    result = check.run(mnist_dataset_train, mnist_dataset_test, mock_trained_mnist,
                       device=device)

    # Assert
    assert_that(result.value, has_length(40))
    assert_that(result.display, has_length(greater_than(0)))

    figure = t.cast(BaseFigure, result.display[0])
    assert_that(figure, instance_of(BaseFigure))

    assert_that(figure.data, assert_class_performance_display(
        xaxis=[
            contains_exactly(equal_to('7'), equal_to('9')),
            contains_exactly(equal_to('7'), equal_to('9')),
            contains_exactly(equal_to('7'), equal_to('9')),
            contains_exactly(equal_to('9'), equal_to('7')),
        ],
        yaxis=[
            contains_exactly(
                close_to(0.980, 0.001),
                close_to(0.965, 0.001),
            ),
            contains_exactly(
                close_to(0.973, 0.001),
                close_to(0.955, 0.001),
            ),
            contains_exactly(
                close_to(0.978, 0.001),
                close_to(0.970, 0.001),
            ),
            contains_exactly(
                close_to(0.975, 0.001),
                close_to(0.972, 0.001),
            )
        ]
    ))


def test_mnist_best(mnist_dataset_train, mnist_dataset_test, mock_trained_mnist, device):
    # Arrange

    check = ClassPerformance(n_to_show=2, show_only='best')
    # Act
    result = check.run(mnist_dataset_train, mnist_dataset_test, mock_trained_mnist,
                       device=device, n_samples=None)

    # Assert
    assert_that(result.value, has_length(40))
    assert_that(result.display, has_length(greater_than(0)))

    figure = t.cast(BaseFigure, result.display[0])
    assert_that(figure, instance_of(BaseFigure))

    assert_that(figure.data, assert_class_performance_display(
        xaxis=[
            contains_exactly(equal_to('6'), equal_to('8')),
            contains_exactly(equal_to('6'), equal_to('8')),
            contains_exactly(equal_to('6'), equal_to('8')),
            contains_exactly(equal_to('8'), equal_to('6')),
        ],
        yaxis=[
            contains_exactly(
                close_to(0.989, 0.001),
                close_to(0.968, 0.001),
            ),
            contains_exactly(
                close_to(0.988, 0.001),
                close_to(0.984, 0.001),
            ),
            contains_exactly(
                close_to(0.984, 0.001),
                close_to(0.970, 0.001),
            ),
            contains_exactly(
                close_to(0.990, 0.001),
                close_to(0.989, 0.001),
            )
        ]
    ))


def test_mnist_alt(mnist_dataset_train, mnist_dataset_test, mock_trained_mnist, device):
    # Arrange

    check = ClassPerformance(n_to_show=2,
                             alternative_metrics={'p': Precision(), 'r': Recall()})
    # Act
    result = check.run(mnist_dataset_train, mnist_dataset_test, mock_trained_mnist,
                       device=device)

    # Assert
    assert_that(result.value, has_length(40))
    assert_that(result.display, has_length(greater_than(0)))
    assert_that(set(result.value['Metric']), equal_to({'p', 'r'}))

    figure = t.cast(BaseFigure, result.display[0])
    assert_that(figure, instance_of(BaseFigure))

    assert_that(figure.data, assert_class_performance_display(
        metrics=('r', 'p'),
        xaxis=[
            contains_exactly(equal_to('1'), equal_to('2')),
            contains_exactly(equal_to('2'), equal_to('1')),
            contains_exactly(equal_to('2'), equal_to('1')),
            contains_exactly(equal_to('2'), equal_to('1')),
        ],
        yaxis=[
            contains_exactly(
                close_to(0.987, 0.001),
                close_to(0.987, 0.001),
            ),
            contains_exactly(
                close_to(0.981, 0.001),
                close_to(0.972, 0.001),
            ),
            contains_exactly(
                close_to(0.988, 0.001),
                close_to(0.987, 0.001),
            ),
            contains_exactly(
                close_to(0.984, 0.001),
                close_to(0.980, 0.001),
            )
        ]
    ))


def test_coco_best(coco_train_visiondata, coco_test_visiondata, mock_trained_yolov5_object_detection, device):
    # Arrange
    check = ClassPerformance(n_to_show=2, show_only='best')
    # Act
    result = check.run(coco_train_visiondata, coco_test_visiondata,
                       mock_trained_yolov5_object_detection, device=device)

    # Assert
    assert_that(result.value, has_length(236))
    assert_that(set(result.value['Metric']), equal_to({'Average Precision', 'Average Recall'}))
    assert_that(result.display, has_length(greater_than(0)))

    figure = t.cast(BaseFigure, result.display[0])
    assert_that(figure, instance_of(BaseFigure))

    assert_that(figure.data, assert_class_performance_display(
        metrics=('Average Precision', 'Average Recall'),
        xaxis=[
            contains_exactly(equal_to('suitcase')),
            contains_exactly(equal_to('suitcase')),
            contains_exactly(equal_to('suitcase'), equal_to('bear')),
            contains_exactly(equal_to('suitcase'), equal_to('bear')),
        ],
        yaxis=[
            contains_exactly(
                close_to(0.234, 0.001),
            ),
            contains_exactly(
                close_to(0.233, 0.001),
            ),
            contains_exactly(
                close_to(1.0, 0.001),
                close_to(0.9, 0.001),
            ),
            contains_exactly(
                close_to(1.0, 0.001),
                close_to(0.9, 0.001),
            )
        ]
    ))


def test_class_list(mnist_dataset_train, mnist_dataset_test, mock_trained_mnist, device):
    # Arrange

    check = ClassPerformance(class_list_to_show=[1])
    # Act
    result = check.run(mnist_dataset_train, mnist_dataset_test, mock_trained_mnist,
                       device=device)

    # Assert
    assert_that(result.value, has_length(40))
    assert_that(set(result.value['Class']), equal_to(set(range(10))))

    assert_that(result.display, has_length(greater_than(0)))

    figure = t.cast(BaseFigure, result.display[0])
    assert_that(figure, instance_of(BaseFigure))

    assert_that(figure.data, assert_class_performance_display(
        xaxis=[
            contains_exactly(equal_to('1')),
            contains_exactly(equal_to('1')),
            contains_exactly(equal_to('1')),
            contains_exactly(equal_to('1')),
        ],
        yaxis=[
            contains_exactly(
                close_to(0.987, 0.001),
            ),
            contains_exactly(
                close_to(0.972, 0.001),
            ),
            contains_exactly(
                close_to(0.987, 0.001),
            ),
            contains_exactly(
                close_to(0.980, 0.001),
            )
        ]
    ))



def test_condition_test_performance_greater_than_pass(mnist_dataset_train,
                                                       mnist_dataset_test,
                                                       mock_trained_mnist,
                                                       device):
    # Arrange
    check = ClassPerformance().add_condition_test_performance_greater_than(0.5)

    # Act
    result = check.run(mnist_dataset_train, mnist_dataset_test, mock_trained_mnist,
                       device=device)

    assert_that(result.conditions_results, has_items(
        equal_condition_result(is_pass=True,
                               details='Found minimum score for Recall metric of value 0.97 for class 9',
                               name='Scores are greater than 0.5'))
    )


def test_condition_test_performance_greater_than_fail(
    mnist_dataset_train,
    mnist_dataset_test,
    mock_trained_mnist,
    device
):
    # Arrange
    check = ClassPerformance(
        n_to_show=2,
        alternative_metrics={'p': Precision(), 'r': Recall()}
    ).add_condition_test_performance_greater_than(1)

    # Act
    result = check.run(mnist_dataset_train, mnist_dataset_test, mock_trained_mnist,
                       device=device)

    assert_that(result.conditions_results, has_items(
        equal_condition_result(
            is_pass=False,
            details=re.compile(r"Found metrics with scores below threshold:.*"),
            name='Scores are greater than 1'
        )
    ))


def test_condition_train_test_relative_degradation_less_than_pass(
    mnist_dataset_train,
    mnist_dataset_test,
    mock_trained_mnist,
    device
):
    # Arrange
    check = ClassPerformance().add_condition_train_test_relative_degradation_less_than(0.1)

    # Act
    result = check.run(mnist_dataset_train, mnist_dataset_test, mock_trained_mnist,
                       device=device)

    assert_that(result.conditions_results, has_items(
        equal_condition_result(
            is_pass=True,
            details='Found max degradation of 0.86% for metric Precision and class 5',
            name='Train-Test scores relative degradation is less than 0.1'
        )
    ))


def test_condition_train_test_relative_degradation_less_than_fail(
    mnist_dataset_train,
    mnist_dataset_test,
    mock_trained_mnist,
    device
):
    # Arrange
    check = ClassPerformance().add_condition_train_test_relative_degradation_less_than(0.0001)

    # Act
    result = check.run(mnist_dataset_train, mnist_dataset_test, mock_trained_mnist,
                       device=device)

    assert_that(result.conditions_results, has_items(
        equal_condition_result(
            is_pass=False,
            name='Train-Test scores relative degradation is less than 0.0001',
            details=(
                '10 classes scores failed. Found max degradation of 0.86% for metric Precision '
                'and class 5'
            )
        )
    ))


def test_condition_class_performance_imbalance_ratio_less_than(
    mnist_dataset_train,
    mnist_dataset_test,
    mock_trained_mnist,
    device
):
    # Arrange
    check = ClassPerformance().add_condition_class_performance_imbalance_ratio_less_than(0.5, 'Precision')

    # Act
    result = check.run(mnist_dataset_train, mnist_dataset_test, mock_trained_mnist,
                       device=device)

    assert_that(result.conditions_results, has_items(
        equal_condition_result(
            is_pass=True,
            name='Relative ratio difference between labels \'Precision\' score is less than 50%',
            details='Relative ratio difference between highest and lowest in Test dataset classes '
                    'is 1.78%, using Precision metric. Lowest class - 7: 0.97; Highest class - 8: '
                    '0.99\nRelative ratio difference between highest and lowest in Train dataset '
                    'classes is 3.78%, using Precision metric. Lowest class - 9: 0.96; Highest class'
                    ' - 6: 0.99'
        )
    ))


def test_condition_class_performance_imbalance_ratio_less_than_fail(
    mnist_dataset_train,
    mnist_dataset_test,
    mock_trained_mnist,
    device
):
    # Arrange
    check = ClassPerformance() \
        .add_condition_class_performance_imbalance_ratio_less_than(0.0001, 'Precision')

    # Act
    result = check.run(mnist_dataset_train, mnist_dataset_test, mock_trained_mnist,
                       device=device)

    assert_that(result.conditions_results, has_items(
        equal_condition_result(is_pass=False,
                               details='Relative ratio difference between highest and lowest in Test dataset classes '
                                       'is 1.78%, using Precision metric. Lowest class - 7: 0.97; Highest class - 8: '
                                       '0.99\nRelative ratio difference between highest and lowest in Train dataset '
                                       'classes is 3.78%, using Precision metric. Lowest class - 9: 0.96; Highest class'
                                       ' - 6: 0.99',
                               name='Relative ratio difference between labels \'Precision\' score is less than 0.01%'))
    )


def test_custom_task(mnist_train_custom_task, mnist_test_custom_task, device, mock_trained_mnist):
    # Arrange
    metrics = {'metric': Precision()}
    check = ClassPerformance(alternative_metrics=metrics)

    # Act & Assert - check runs without errors
    check.run(mnist_train_custom_task, mnist_test_custom_task, model=mock_trained_mnist, device=device)