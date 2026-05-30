# 导入标准库
import json
import os
# 导入 PyTorch
import torch
# 导入日志
import sys, os

project_root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root_path)
from base import logger
# 导入numpy
import numpy as np
# 导入 Transformers 库
from transformers import BertTokenizer, BertForSequenceClassification
from transformers import Trainer, TrainingArguments
# 导入train_test_split
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix


class QueryClassifier:
    def __init__(self, model_path="bert_query_classifier"):
        # 初始化模型路径
        self.model_path = model_path
        # 加载BERT分词器
        rag_qa_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        models_path = os.path.join(rag_qa_path, 'models')
        self.base_model_path = os.path.join(models_path, 'bert-base-chinese')
        self.tokenizer = BertTokenizer.from_pretrained(self.base_model_path)
        # 初始化模型参数
        self.model = None
        # 确定设备
        if torch.cuda.is_available():
            self.device = torch.device('cuda')
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            self.device = torch.device('mps')
        else:
            self.device = torch.device('cpu')
        # 记录设备信息
        logger.info(f'使用设备: {self.device}')
        # 定义标签映射
        self.label_map = {'通用知识': 0, '专业咨询': 1}
        # 加载模型
        self.load_model()

    def load_model(self):
        if os.path.exists(self.model_path):
            # 加载训练好的模型
            self.model = BertForSequenceClassification.from_pretrained(self.model_path)
            # 将模型迁移到指定的设备上
            self.model.to(self.device)
            # 打印日志记录信息
            logger.info(f'成功加载模型: {self.model_path}')
        else:
            # 初始化未训练的模型
            self.model = BertForSequenceClassification.from_pretrained(self.base_model_path, num_labels=2)
            # 将模型迁移到指定的设备上
            self.model.to(self.device)
            # 记录初始化模型日志
            logger.info('BERT模型 初始化成功')

    def save_model(self):
        """保存模型"""
        self.model.save_pretrained(self.model_path)
        self.tokenizer.save_pretrained(self.model_path)
        logger.info(f"模型保存至: {self.model_path}")

    def preprocess_data(self, texts, labels):
        # 对文本进行编码 -> 向量
        encodings = self.tokenizer(texts, truncation=True, padding='max_length', max_length=128, return_tensors='pt')

        # 将labels -> 数字
        labels = [self.label_map[label] for label in labels]

        return encodings, labels

    def create_dataset(self, encodings, labels):
        class Dataset(torch.utils.data.Dataset):
            def __init__(self, encodings, labels):
                self.encodings = encodings
                self.labels = labels

            def __getitem__(self, idx):
                item = {key: val[idx] for key, val in self.encodings.items()}
                item["labels"] = torch.tensor(self.labels[idx])
                return item

            def __len__(self):
                return len(self.labels)

        return Dataset(encodings, labels)

    def train_model(self, train_data_path='../classifier_data/model_generic_5000.json'):
        if not os.path.exists(train_data_path):
            logger.error(f'数据集不存在: {train_data_path}')
            raise FileNotFoundError(f'数据集文件不存在: {train_data_path}')
        with open(train_data_path, 'r', encoding='utf-8') as src_f:
            data = [json.loads(line) for line in src_f.readlines() if line.strip()]

        # 提取 query 和 label
        texts = [i['query'] for i in data]
        labels = [i['label'] for i in data]

        # 划分训练数据 和 测试数据
        train_texts, val_texts, train_labels, val_labels = train_test_split(
            texts,
            labels,
            test_size=0.2,
            random_state=42,
            stratify=labels
        )

        # 对训练数据和评估数据进行编码
        train_encodings, train_labels = self.preprocess_data(train_texts, train_labels)
        val_encodings, val_labels = self.preprocess_data(val_texts, val_labels)

        # 创建dataset对象
        train_dataset = self.create_dataset(train_encodings, train_labels)
        val_dataset = self.create_dataset(val_encodings, val_labels)

        # 设置训练参数
        training_args = TrainingArguments(
            output_dir=os.path.join(os.path.dirname(os.path.abspath(self.model_path)), "bert_results"),
            num_train_epochs=3,
            per_device_train_batch_size=8,
            per_device_eval_batch_size=8,
            warmup_steps=20,
            weight_decay=0.01,
            logging_dir=os.path.join(os.path.dirname(os.path.abspath(self.model_path)), "bert_logs"),
            logging_steps=10,
            eval_strategy="epoch",
            # evaluation_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
            save_total_limit=1,  # 只保存一个检查点，即最优的模型
            metric_for_best_model="eval_loss",
            fp16=False,  # 禁用混合精度
            report_to="none",
        )

        # 初始化 Trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            compute_metrics=self.compute_metrics
        )

        # 训练模型
        logger.info("开始训练 BERT 模型...")
        trainer.train()
        self.save_model()

        # 模型效果评估
        self.evaluate_model(val_texts, val_labels)

    def compute_metrics(self, eval_pred):
        # 获得预测结果概率 和 标签
        logits, labels = eval_pred
        # 得到预测结果
        pred_labels = np.argmax(logits, axis=-1)
        # 计算准确率并返回
        accuracy = (pred_labels == labels).mean()
        return {'accuracy': accuracy}

    def evaluate_model(self, texts, true_labels):
        """评估模型性能"""
        encodings = self.tokenizer(
            texts,
            truncation=True,
            padding='max_length',
            max_length=128,
            return_tensors='pt'
        )

        dataset = self.create_dataset(encodings, true_labels)

        trainer = Trainer(model=self.model)
        predictions = trainer.predict(dataset)
        pre_labels = np.argmax(predictions.predictions, axis=-1)

        logger.info('query_classifier分类报告: ')
        logger.info(classification_report(
            true_labels,
            pre_labels,
            target_names=['通用知识', '专业咨询'],
            zero_division=0
        ))
        logger.info('混淆矩阵')
        logger.info(confusion_matrix(true_labels, pre_labels))

    def predict_model(self, query):
        if self.model == None:
            logger.info('query_classifier模型加载失败')
            # 默认返回通用知识
            return '通用知识'
        # 对query进行编码处理
        inputs = self.tokenizer(query, truncation=True, padding='max_length', max_length=128,
                                return_tensors='pt').to(self.device)
        # 模型预测
        self.model.eval()
        with torch.no_grad():
            logits = self.model(**inputs).logits
        return '通用知识' if torch.argmax(logits, axis=-1).item() == 0 else '专业咨询'


if __name__ == '__main__':
    classifier = QueryClassifier()
    # print(classifier.model)
    # classifier.train_model()
    print(classifier.predict_model('AI是什么'))
