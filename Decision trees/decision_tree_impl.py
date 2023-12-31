import numpy as np
from collections import Counter


def find_best_split(feature_vector, target_vector):
    total_vector = np.column_stack((feature_vector, target_vector))
    total_vector = total_vector[total_vector[:,0].argsort()]
    feature_values = np.unique(total_vector[:, 0])
    kernel = [0.5, 0.5]
    thresholds = np.convolve(feature_values, kernel, mode='valid')
    sorted_target = total_vector[:, 1]
    bound = np.append(total_vector[:, 0], total_vector[:, 0][-1])

    total_obj = len(target_vector)
    total_num = np.cumsum(np.ones(len(target_vector)))
    left_ones = np.cumsum(sorted_target)
    left_zeros = total_num - left_ones
    left_total = left_ones + left_zeros
    right_ones = np.sum(sorted_target) - left_ones
    right_zeros = (len(target_vector) - np.sum(sorted_target)) - left_zeros
    right_total = right_ones + right_zeros

    H_left = 1 - (left_ones / left_total)**2 - (left_zeros / left_total)**2
    H_right = 1 - (right_ones / right_total) **2 - (right_zeros / right_total)**2
    ginis =  - (left_total / total_obj) * H_left - (right_total / total_obj) * H_right
    ginis = ginis[(bound[:-1] - bound[1:]) != 0]
    gini_best = np.max(ginis)
    threshold_best = thresholds[np.argmax(ginis)]

    return thresholds, ginis, threshold_best, gini_best


class DecisionTree:
    def __init__(self, feature_types, max_depth=None, min_samples_split=None, min_samples_leaf=None):
        if np.any(list(map(lambda x: x != "real" and x != "categorical", feature_types))):
            raise ValueError("There is unknown feature type")

        self._tree = {}
        self._feature_types = feature_types
        self._max_depth = max_depth
        self._min_samples_split = min_samples_split
        self._min_samples_leaf = min_samples_leaf

    def _fit_node(self, sub_X, sub_y, node, depth):
        if np.all(sub_y == sub_y[0]):
            node["type"] = "terminal"
            node["class"] = sub_y[0]
            return
        if self._max_depth is not None and depth == self._max_depth:
            node["type"] = "terminal"
            node["class"] = Counter(sub_y).most_common(1)[0][0]
            return
        if self._min_samples_split is not None and sub_X.shape[0] < self._min_samples_split:
            node["type"] = "terminal"
            node["class"] = Counter(sub_y).most_common(1)[0][0]
            return
        feature_best, threshold_best, gini_best, split = None, None, None, None
        for feature in range(sub_X.shape[1]):
            feature_type = self._feature_types[feature]
            categories_map = {}

            if feature_type == "real":
                feature_vector = sub_X[:, feature]
            elif feature_type == "categorical":
                counts = Counter(sub_X[:, feature])
                clicks = Counter(sub_X[sub_y == 1, feature])
                ratio = {}
                for key, current_count in counts.items():
                    if key in clicks:
                        current_click = clicks[key]
                    else:
                        current_click = 0
                    ratio[key] = current_click / current_count
                sorted_categories = list(map(lambda x: x[0], sorted(ratio.items(), key=lambda x: x[1])))
                categories_map = dict(zip(sorted_categories, list(range(len(sorted_categories)))))

                feature_vector = np.array(list(map(lambda x: categories_map[x], sub_X[:, feature])))
            else:
                raise ValueError

            if len(np.unique(feature_vector)) == 1:
                continue

            _, _, threshold, gini = find_best_split(feature_vector, sub_y)
            if gini_best is None or gini > gini_best:
                feature_best = feature
                gini_best = gini
                split = feature_vector < threshold

                if feature_type == "real":
                    threshold_best = threshold
                elif feature_type == "categorical":
                    threshold_best = list(map(lambda x: x[0],
                                              filter(lambda x: x[1] < threshold, categories_map.items())))
                else:
                    raise ValueError

        if feature_best is None:
            node["type"] = "terminal"
            node["class"] = Counter(sub_y).most_common(1)[0][0]
            return
        
        if self._min_samples_leaf is not None and (sub_X[split].shape[0] < self._min_samples_leaf or sub_X[np.logical_not(split)].shape[0] < self._min_samples_leaf):
            node["type"] = "terminal"
            node["class"] = Counter(sub_y).most_common(1)[0][0]
            return

        node["type"] = "nonterminal"

        node["feature_split"] = feature_best
        if self._feature_types[feature_best] == "real":
            node["threshold"] = threshold_best
        elif self._feature_types[feature_best] == "categorical":
            node["categories_split"] = threshold_best
        else:
            raise ValueError
        node["left_child"], node["right_child"] = {}, {}
        self._fit_node(sub_X[split], sub_y[split], node["left_child"], depth + 1)
        self._fit_node(sub_X[np.logical_not(split)], sub_y[np.logical_not(split)], node["right_child"], depth + 1)

    def _predict_node(self, x, node):
        while node['type'] != 'terminal':
            if 'threshold' in node:
                if x[node['feature_split']] < node['threshold']:
                    node = node['left_child']
                else:
                    node = node['right_child']
            else:
                if x[node['feature_split']] in node['categories_split']:
                    node = node['left_child']
                else:
                    node = node['right_child']
        return node['class']

    def fit(self, X, y):
        self._fit_node(X, y, self._tree, 0)

    def predict(self, X):
        predicted = []
        for x in X:
            predicted.append(self._predict_node(x, self._tree))
        return np.array(predicted)
