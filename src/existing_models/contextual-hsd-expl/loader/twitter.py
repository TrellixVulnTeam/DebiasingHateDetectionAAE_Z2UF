from .common import *
from torch.utils.data import DataLoader, Dataset
import torch
import csv
import pandas as pd

class TwitterProcessor(DataProcessor):
    """
    Data processor using DataProcessor class provided by BERT
    is_hate= use is_hate label, (combined)
    otherwise use is_harassment (combined_harassment)
    """
    def __init__(self, configs, feat_col, label_col, tokenizer=None):
        super().__init__()
        self.data_dir = configs.data_dir
        self.label_groups = [0,1]
        self.tokenizer = tokenizer
        self.max_seq_length = configs.max_seq_length
        self.configs = configs
        self.text_col = feat_col
        self.label_col = label_col

    def _create_examples(self, data_dir, split, label=None):
        """
        Create a list of InputExample, where .text_a is raw text and .label is specified
        as configs.label_groups
        :param data_dir:
        :param split:
        :param label:
        :return:
        """
        f = open(os.path.join(data_dir, '%s.csv' % split), encoding="utf-8")
        reader = csv.reader(f, delimiter=',')
        next(reader) # skip header
        examples = []
        for i, row in enumerate(reader):
            example = InputExample(text_a=row[self.text_col], guid='%s-%s' % (split, i))
            label = int(row[self.label_col])
            example.label = label
            examples.append(example)
        f.close()
        return examples

    def get_train_examples(self, data_dir, label=None):
        return self._create_examples(data_dir, 'train', label)

    def get_dev_examples(self, data_dir, label=None):
        return self._create_examples(data_dir, 'dev', label)

    def get_test_examples(self, data_dir, label=None):
        return self._create_examples(data_dir, 'test', label)

    @staticmethod
    def get_is_aae(data_dir, split, labels=['is_aae_08', 'is_aae_06']):
        temp = pd.read_csv(os.path.join(data_dir, f'{split}.csv'))
        return temp[labels[0]].values, temp[labels[1]].values

    def get_example_from_tensor_dict(self, tensor_dict):
        raise NotImplementedError

    def get_labels(self):
        return [0,1]

    def get_features(self, split):
        """
        Return a list of dict, where each dict contains features to be fed into the BERT model
        for each instance. ['text'] is a LongTensor of length configs.max_seq_length, either truncated
        or padded with 0 to match this length.
        :param split: 'train' or 'dev'
        :return:
        """
        examples = self._create_examples(self.data_dir, split)
        features = []
        for example in examples:
            tokens = self.tokenizer.tokenize(example.text_a)
            if len(tokens) > self.max_seq_length - 2:
                tokens = tokens[:(self.max_seq_length - 2)]
            tokens = ["[CLS]"] + tokens + ["[SEP]"]
            input_ids = self.tokenizer.convert_tokens_to_ids(tokens)
            padding = [0] * (self.max_seq_length - len(input_ids))
            input_ids += padding
            input_ids = torch.LongTensor(input_ids)
            #
            features.append({'text': input_ids, 'length': len(tokens)})
        return features

    def get_dataloader(self, split, batch_size=1):
        """
        return a torch.utils.DataLoader instance, mainly used for training the language model.
        :param split:
        :param batch_size:
        :return:
        """
        features = self.get_features(split)
        dataset = TwitterDataset(features)
        dataloader = DataLoader(dataset, batch_size=batch_size, collate_fn=dotdict_collate)
        return dataloader

    def set_tokenizer(self, tokenizer):
        self.tokenizer = tokenizer


class TwitterDataset(Dataset):
    """
    torch.utils.Dataset instance for building torch.utils.DataLoader, for training the language model.
    """
    def __init__(self, features):
        super().__init__()
        self.features = features

    def __getitem__(self, item):
        return self.features[item]

    def __len__(self):
        return len(self.features)
