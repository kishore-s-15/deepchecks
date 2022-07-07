# ----------------------------------------------------------------------------
# Copyright (C) 2021-2022 Deepchecks (https://www.deepchecks.com)
#
# This file is part of Deepchecks.
# Deepchecks is distributed under the terms of the GNU Affero General
# Public License (version 3 or later).
# You should have received a copy of the GNU Affero General Public License
# along with Deepchecks.  If not, see <http://www.gnu.org/licenses/>.
# ----------------------------------------------------------------------------
#
"""Module containing simple comparison check."""
from typing import Any, Dict, Hashable, List

import numpy as np
import pandas as pd
import plotly.express as px
import torch
from ignite.metrics import Fbeta

from deepchecks.core import CheckResult, ConditionCategory, ConditionResult, DatasetKind
from deepchecks.core.errors import DeepchecksValueError
from deepchecks.utils import plot
from deepchecks.tabular.metric_utils.metrics import get_gain
from deepchecks.utils.strings import format_percent
from deepchecks.vision import Batch, Context, TrainTestCheck
from deepchecks.vision.metrics_utils import get_scorers_list, metric_results_to_df
from deepchecks.vision.metrics_utils.metrics import filter_classes_for_display
from deepchecks.vision.vision_data import TaskType

__all__ = ['SimpleModelComparison']


_allowed_strategies = (
    'most_frequent',
    'prior',
    'stratified',
    'uniform'
)


class SimpleModelComparison(TrainTestCheck):
    """Compare given model score to simple model score (according to given model type).

    For classification models, the simple model is a dummy classifier the selects the predictions based on a strategy.


    Parameters
    ----------
    strategy : str, default='prior'
        Strategy to use to generate the predictions of the simple model.

        * 'most_frequent' : The most frequent label in the training set is predicted.
          The probability vector is 1 for the most frequent label and 0 for the other predictions.
        * 'prior' : The probability vector always contains the empirical class prior distribution (i.e. the class
          distribution observed in the training set).
        * 'stratified' : The predictions are generated by sampling one-hot vectors from a multinomial distribution
          parametrized by the empirical class prior probabilities.
        * 'uniform' : Generates predictions uniformly at random from the list of unique classes observed in y,
          i.e. each class has equal probability. The predicted class is chosen randomly.
    alternative_metrics : Dict[str, Metric], default: None
        A dictionary of metrics, where the key is the metric name and the value is an ignite.Metric object whose score
        should be used. If None are given, use the default metrics.
    n_to_show : int, default: 20
        Number of classes to show in the report. If None, show all classes.
    show_only : str, default: 'largest'
        Specify which classes to show in the report. Can be one of the following:
        - 'largest': Show the largest classes.
        - 'smallest': Show the smallest classes.
        - 'random': Show random classes.
        - 'best': Show the classes with the highest score.
        - 'worst': Show the classes with the lowest score.
    metric_to_show_by : str, default: None
        Specify the metric to sort the results by. Relevant only when show_only is 'best' or 'worst'.
        If None, sorting by the first metric in the default metrics list.
    class_list_to_show: List[int], default: None
        Specify the list of classes to show in the report. If specified, n_to_show, show_only and metric_to_show_by
        are ignored.

    """

    _state: Dict[Hashable, Any] = {}

    def __init__(self,
                 strategy: str = 'most_frequent',
                 alternative_metrics=None,
                 n_to_show: int = 20,
                 show_only: str = 'largest',
                 metric_to_show_by: str = None,
                 class_list_to_show: List[int] = None,
                 **kwargs):
        super().__init__(**kwargs)
        self.strategy = strategy

        if self.strategy not in _allowed_strategies:
            raise DeepchecksValueError(
                f'Unknown strategy type: {self.strategy}, expected one of{_allowed_strategies}.'
            )

        self.alternative_metrics = alternative_metrics
        self.n_to_show = n_to_show
        self.class_list_to_show = class_list_to_show

        if self.class_list_to_show is None:
            if show_only not in ['largest', 'smallest', 'random', 'best', 'worst']:
                raise DeepchecksValueError(f'Invalid value for show_only: {show_only}. Should be one of: '
                                           f'["largest", "smallest", "random", "best", "worst"]')

            self.show_only = show_only
            if alternative_metrics is not None and show_only in ['best', 'worst'] and metric_to_show_by is None:
                raise DeepchecksValueError('When alternative_metrics are provided and show_only is one of: '
                                           '["best", "worst"], metric_to_show_by must be specified.')

        self.metric_to_show_by = metric_to_show_by
        self._test_metrics = None
        self._perfect_metrics = None

    def initialize_run(self, context: Context):
        """Initialize the metrics for the check, and validate task type is relevant."""
        context.assert_task_type(TaskType.CLASSIFICATION)

        if self.alternative_metrics is None:
            self._test_metrics = {'F1': Fbeta(beta=1, average=False)}
            self._perfect_metrics = {'F1': Fbeta(beta=1, average=False)}
        else:
            self._test_metrics = get_scorers_list(context.train, self.alternative_metrics)
            self._perfect_metrics = get_scorers_list(context.train, self.alternative_metrics)

    def update(self, context: Context, batch: Batch, dataset_kind: DatasetKind):
        """Update the metrics for the check."""
        if dataset_kind == DatasetKind.TEST and context.train.task_type == TaskType.CLASSIFICATION:
            label = batch.labels
            prediction = batch.predictions
            for _, metric in self._test_metrics.items():
                metric.update((prediction, label))

            # calculating perfect scores
            n_of_classes = batch.predictions.cpu().detach().shape[1]
            perfect_predictions = np.eye(n_of_classes)[label.cpu().detach().numpy()]
            for _, metric in self._perfect_metrics.items():
                metric.update((torch.Tensor(perfect_predictions).to(context.device), label))

    def compute(self, context: Context) -> CheckResult:
        """Compute the metrics for the check."""
        results = []

        metrics_to_eval = {
            'Given Model': self._test_metrics,
            'Perfect Model': self._perfect_metrics,
            'Simple Model': self._generate_simple_model_metrics(context.train, context.test)
        }
        for name, metrics in metrics_to_eval.items():
            dataset = context.get_data_by_kind(DatasetKind.TEST)
            metrics_df = metric_results_to_df(
                {k: m.compute() for k, m in metrics.items()}, dataset
            )
            metrics_df['Model'] = name
            metrics_df['Number of samples'] = metrics_df['Class'].map(dataset.n_of_samples_per_class.get)
            results.append(metrics_df)

        results_df = pd.concat(results)
        results_df = results_df[['Model', 'Metric', 'Class', 'Class Name', 'Number of samples', 'Value']]

        results_df.dropna(inplace=True)
        results_df.sort_values(by=['Model', 'Value'], ascending=False, inplace=True)
        results_df.reset_index(drop=True, inplace=True)

        if context.with_display:
            if not self.metric_to_show_by:
                self.metric_to_show_by = list(self._test_metrics.keys())[0]
            if self.class_list_to_show is not None:
                display_df = results_df.loc[results_df['Class'].isin(self.class_list_to_show)]
            elif self.n_to_show is not None:
                rows = results_df['Class'].isin(filter_classes_for_display(
                    results_df.loc[results_df['Model'] != 'Perfect Model'],
                    self.metric_to_show_by,
                    self.n_to_show,
                    self.show_only,
                    column_to_filter_by='Model',
                    column_filter_value='Given Model'
                ))
                display_df = results_df.loc[rows]
            else:
                display_df = results_df

            fig = (
                px.histogram(
                    display_df.loc[results_df['Model'] != 'Perfect Model'],
                    x='Class Name',
                    y='Value',
                    color='Model',
                    color_discrete_sequence=(plot.colors['Generated'], plot.colors['Baseline']),
                    barmode='group',
                    facet_col='Metric',
                    facet_col_spacing=0.05,
                    hover_data=['Number of samples'],
                    title=f'Simple Model (Strategy: {self.strategy}) vs. Given Model')
                .update_xaxes(title=None, type='category')
                .update_yaxes(title=None, matches=None)
                .for_each_annotation(lambda a: a.update(text=a.text.split('=')[-1]))
                .for_each_yaxis(lambda yaxis: yaxis.update(showticklabels=True))
            )
        else:
            fig = None

        return CheckResult(
            results_df,
            header='Simple Model Comparison',
            display=fig
        )

    def _generate_simple_model_metrics(self, train, test):
        class_prior = np.zeros(train.num_classes)
        n_samples = 0
        for label, total in train.n_of_samples_per_class.items():
            class_prior[label] = total
            n_samples += total
        class_prior /= n_samples

        if self.strategy == 'most_frequent':
            dummy_prediction = np.zeros(train.num_classes)
            dummy_prediction[np.argmax(class_prior)] = 1
            dummy_predictor = lambda: torch.from_numpy(dummy_prediction)
        elif self.strategy == 'prior':
            dummy_predictor = lambda: torch.from_numpy(class_prior)
        elif self.strategy == 'stratified':
            dummy_predictor = lambda: torch.from_numpy(np.random.multinomial(1, class_prior))
        elif self.strategy == 'uniform':
            dummy_predictor = lambda: torch.from_numpy(np.ones(train.num_classes) / train.num_classes)
        else:
            raise DeepchecksValueError(
                f'Unknown strategy type: {self.strategy}, expected one of {_allowed_strategies}.'
            )

        # Create dummy predictions
        dummy_predictions = []
        labels = []
        for label, count in test.n_of_samples_per_class.items():
            labels += [label] * count
            for _ in range(count):
                dummy_predictions.append(dummy_predictor())

        # Get scorers
        if self.alternative_metrics is None:
            metrics = {'F1': Fbeta(beta=1, average=False)}
        else:
            metrics = get_scorers_list(train, self.alternative_metrics)
        for _, metric in metrics.items():
            metric.update((torch.stack(dummy_predictions), torch.LongTensor(labels)))
        return metrics

    def add_condition_gain_greater_than(self,
                                        min_allowed_gain: float = 0.1,
                                        max_gain: float = 50,
                                        classes: List[Hashable] = None,
                                        average: bool = False):
        """Add condition - require gain between the model and the simple model to be greater than threshold.

        Parameters
        ----------
        min_allowed_gain : float , default: 0.1
            Minimum allowed gain between the model and the simple model -
            gain is: difference in performance / (perfect score - simple score)
        max_gain : float , default: 50
            the maximum value for the gain value, limits from both sides [-max_gain, max_gain]
        classes : List[Hashable] , default: None
            Used in classification models to limit condition only to given classes.
        average : bool , default: False
            Used in classification models to flag if to run condition on average of classes, or on
            each class individually
        """
        name = f'Model performance gain over simple model is greater than {format_percent(min_allowed_gain)}'
        if classes:
            name = name + f' for classes {str(classes)}'
        return self.add_condition(name,
                                  calculate_condition_logic,
                                  include_classes=classes,
                                  min_allowed_gain=min_allowed_gain,
                                  max_gain=max_gain,
                                  average=average)


def calculate_condition_logic(result, include_classes=None, average=False, max_gain=None,
                              min_allowed_gain=None) -> ConditionResult:
    scores = result.loc[result['Model'] == 'Given Model']
    perfect_scores = result.loc[result['Model'] == 'Perfect Model']
    simple_scores = result.loc[result['Model'] == 'Simple Model']
    metrics = scores['Metric'].unique()

    # Save min gain info to print when condition pass
    min_gain = (np.inf, '')

    def update_min_gain(gain, metric, class_name=None):
        nonlocal min_gain
        if gain < min_gain[0]:
            message = f'Found minimal gain of {format_percent(gain)} for metric {metric}'
            if class_name:
                message += f' and class {class_name}'
            min_gain = gain, message

    fails = {}
    if not average:
        for metric in metrics:
            failed_classes = {}
            for _, scores_row in scores.loc[scores['Metric'] == metric].iterrows():
                curr_class = scores_row['Class']
                curr_class_name = scores_row['Class Name']
                curr_value = scores_row['Value']
                if include_classes and curr_class not in include_classes:
                    continue
                perfect = perfect_scores.loc[(perfect_scores['Metric'] == metric) &
                                             (perfect_scores['Class'] == curr_class)]['Value'].values[0]
                if curr_value == perfect:
                    continue

                simple_score_value = simple_scores.loc[(simple_scores['Class'] == curr_class) &
                                                       (simple_scores['Metric'] == metric)]['Value'].values[0]
                gain = get_gain(simple_score_value,
                                curr_value,
                                perfect,
                                max_gain)
                update_min_gain(gain, metric, curr_class_name)
                if gain <= min_allowed_gain:
                    failed_classes[curr_class_name] = format_percent(gain)

            if failed_classes:
                fails[metric] = failed_classes
    else:
        scores = average_scores(scores, simple_scores, include_classes)
        for metric, models_scores in scores.items():
            metric_perfect_score = perfect_scores.loc[(perfect_scores['Metric'] == metric)]['Value'].values[0]
            # If origin model is perfect, skip the gain calculation
            if models_scores['Origin'] == metric_perfect_score:
                continue
            gain = get_gain(models_scores['Simple'],
                            models_scores['Origin'],
                            metric_perfect_score,
                            max_gain)
            update_min_gain(gain, metric)
            if gain <= min_allowed_gain:
                fails[metric] = format_percent(gain)

    if fails:
        msg = f'Found metrics with gain below threshold: {fails}'
        return ConditionResult(ConditionCategory.FAIL, msg)
    else:
        return ConditionResult(ConditionCategory.PASS, min_gain[1])


def average_scores(scores, simple_model_scores, include_classes):
    """
    Calculate the average of the scores for each metric for all classes.

    Parameters
    ----------
    scores : pd.DataFrame
        the scores for the given model
    simple_model_scores : pd.DataFrame
        the scores for the simple model
    include_classes : List[Hashable]
        the classes to include in the calculation

    Returns
    -------
    Dictionary[str, Dictionary[str, float]]
        the average scores for each metric. The keys are the metric names, and the values are a dictionary
        with the keys being Origin and Simple and the values being the average score.
    """
    result = {}
    metrics = scores['Metric'].unique()
    for metric in metrics:
        model_score = 0
        simple_score = 0
        total = 0
        for _, row in scores.loc[scores['Metric'] == metric].iterrows():
            if include_classes and row['Class'] not in include_classes:
                continue
            model_score += row['Value']
            simple_score += simple_model_scores.loc[(simple_model_scores['Class'] == row['Class']) &
                                                    (simple_model_scores['Metric'] == metric)]['Value'].values[0]
            total += 1

        result[metric] = {
            'Origin': model_score / total,
            'Simple': simple_score / total
         }

    return result
