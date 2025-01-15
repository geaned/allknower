import argparse
import json
import os
from typing import Dict, Optional, Tuple

import pandas as pd
import torch
import wandb
from dotenv import load_dotenv
from loguru import logger
from sklearn.metrics import accuracy_score
from sklearn.model_selection import StratifiedGroupKFold
from torch import nn
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

load_dotenv()
WANDB_PROJECT_NAME = "Allknower"


class TripletsDataset(Dataset):
    def __init__(self, df: pd.DataFrame):
        self.data = df
        self.data.loc[:, "label"] = self.data["label"].apply(
            lambda x: 1 if x == "text" else -1
        )
        self.data.loc[:, "query_embedding"] = self.data["query_embedding"].apply(
            lambda x: json.loads(x)
        )
        self.data.loc[:, "text_embedding"] = self.data["text_embedding"].apply(
            lambda x: json.loads(x)
        )
        self.data.loc[:, "image_embedding"] = self.data["image_embedding"].apply(
            lambda x: json.loads(x)
        )

    def __len__(self):
        return len(self.data)

    def __getitem__(
        self, index: int
    ) -> Tuple[str, torch.Tensor, str, torch.Tensor, str, torch.Tensor, torch.Tensor]:
        query = self.data.loc[index, "query"]
        query_embedding = torch.as_tensor(self.data.loc[index, "query_embedding"])
        text = self.data.loc[index, "text"]
        text_embedding = torch.as_tensor(self.data.loc[index, "text_embedding"])
        image = self.data.loc[index, "image"]
        image_embedding = torch.as_tensor(self.data.loc[index, "image_embedding"])

        # 1 - 'text', -1 - 'image'
        label = torch.as_tensor(self.data.loc[index, "label"])
        return (
            query,
            query_embedding,
            text,
            text_embedding,
            image,
            image_embedding,
            label,
        )


class EmbeddingTower(nn.Module):
    def __init__(self, emb_in_dim: int, emb_out_dim: int, hidden_dim: int):
        super().__init__()
        self.emb_in_dim = emb_in_dim
        self.emb_out_dim = emb_out_dim
        self.hidden_dim = hidden_dim

        self.model = nn.Sequential(
            nn.Linear(self.emb_in_dim, self.hidden_dim),
            nn.BatchNorm1d(self.hidden_dim),
            nn.ReLU(),
            nn.Linear(self.hidden_dim, self.hidden_dim),
            nn.BatchNorm1d(self.hidden_dim),
            nn.ReLU(),
            nn.Linear(self.hidden_dim, self.emb_out_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.model(x)


class BlenderModel(nn.Module):
    def __init__(
        self,
        query_emb_dim: int,
        text_emb_dim: int,
        image_emb_dim: int,
        towers_hidden_dim: int = 512,
        latent_emb_dim: int = 512,
    ):
        super().__init__()
        self.query_tower = EmbeddingTower(
            query_emb_dim, latent_emb_dim, towers_hidden_dim
        )
        self.text_tower = EmbeddingTower(
            text_emb_dim, latent_emb_dim, towers_hidden_dim
        )
        self.image_tower = EmbeddingTower(
            image_emb_dim, latent_emb_dim, towers_hidden_dim
        )

    @classmethod
    def from_config(cls, config: Dict) -> "BlenderModel":
        return cls(
            config["query_emb_dim"],
            config["text_emb_dim"],
            config["image_emb_dim"],
            config["towers_hidden_dim"],
            config["latent_emb_dim"],
        )

    def forward(
        self,
        query_emb: torch.Tensor,
        text_embs: Optional[torch.Tensor] = None,
        image_embs: Optional[torch.Tensor] = None,
        *,
        return_latents: bool = False,
    ) -> Dict[str, torch.Tensor]:
        """
        Expected shapes:
        query_embs - (batch_size, latent_emb_dim)
        text_embs - (batch_size, latent_emb_dim)
        image_embs - (batch_size, latent_emb_dim)
        """
        outputs = {}

        query_latents = self.query_tower(query_emb)
        if return_latents:
            outputs["query_latents"] = query_latents

        if text_embs is not None:
            text_latents = self.text_tower(text_embs)
            if return_latents:
                outputs["text_latents"] = text_latents
            text_scores = (text_latents * query_latents).sum(dim=1)
            outputs["text_scores"] = text_scores

        if image_embs is not None:
            image_latents = self.image_tower(image_embs)
            if return_latents:
                outputs["image_latents"] = image_latents
            image_scores = (image_latents * query_latents).sum(dim=1)
            outputs["image_scores"] = image_scores

        return outputs


class PairwiseLogisticLoss(nn.Module):
    def __init__(self):
        super().__init__()
        self.sigmoid = nn.Sigmoid()

    def forward(
        self,
        pred_score_1: torch.Tensor,
        pred_score_2: torch.Tensor,
        label: torch.Tensor,
    ) -> torch.Tensor:
        score_diff = pred_score_1 - pred_score_2
        loss = -torch.mean(torch.log(self.sigmoid(label * score_diff)))
        return loss


def train(
    training_config: dict,
    model: BlenderModel,
    train_dataset: TripletsDataset,
    val_dataset: TripletsDataset,
) -> None:
    with wandb.init(project=WANDB_PROJECT_NAME, config=training_config):
        device = torch.device(os.environ["BLENDER_TRAINING_DEVICE"])
        model.to(device)
        train_dataloader = DataLoader(
            train_dataset,
            batch_size=training_config["batch_size"],
            shuffle=True,
            num_workers=8,
            pin_memory=True,
            drop_last=True,
        )
        val_dataloader = DataLoader(
            val_dataset,
            batch_size=training_config["batch_size"],
            shuffle=False,
            num_workers=8,
            pin_memory=True,
            drop_last=False,
        )
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)
        criterion = PairwiseLogisticLoss()

        step = 0
        for epoch in range(training_config["n_epochs"]):
            # training
            model.train()
            for batch in tqdm(train_dataloader, desc=f"Epoch {epoch}"):
                (
                    query,
                    query_embedding,
                    text,
                    text_embedding,
                    image,
                    image_embedding,
                    label,
                ) = batch

                outputs = model(
                    query_embedding.to(device),
                    text_embs=text_embedding.to(device),
                    image_embs=image_embedding.to(device),
                )
                text_scores = outputs["text_scores"]
                image_scores = outputs["image_scores"]
                loss = criterion(text_scores, image_scores, label.float().to(device))
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                step += 1

                wandb.log({"epoch": epoch, "train_loss": loss.cpu().item()}, step=step)

            # validation
            model.eval()
            text_scores = []
            image_scores = []
            gt_labels = []

            with torch.no_grad():
                for batch in val_dataloader:
                    (
                        query,
                        query_embedding,
                        text,
                        text_embedding,
                        image,
                        image_embedding,
                        label,
                    ) = batch

                    outputs = model(
                        query_embedding.to(device),
                        text_embs=text_embedding.to(device),
                        image_embs=image_embedding.to(device),
                    )
                    text_scores.extend(outputs["text_scores"].cpu().tolist())
                    image_scores.extend(outputs["image_scores"].cpu().tolist())
                    gt_labels.extend(label.tolist())

            text_scores = torch.as_tensor(text_scores)
            image_scores = torch.as_tensor(image_scores)

            # calculate accuracy_score
            pred_labels = (text_scores > image_scores).to(torch.int)
            gt_labels_0_1 = ((torch.as_tensor(gt_labels) + 1) / 2).round()
            val_accuracy = accuracy_score(pred_labels, gt_labels_0_1)
            val_loss = (
                criterion(
                    text_scores.to(device),
                    image_scores.to(device),
                    torch.as_tensor(gt_labels).to(device),
                )
                .cpu()
                .item()
            )

            logits = text_scores - image_scores
            pred_probas = torch.zeros((len(logits), 2), dtype=torch.float32)
            pred_probas[:, 0] = 1 - logits.sigmoid()
            pred_probas[:, 1] = logits.sigmoid()
            # plot ROC curve
            plot = wandb.plot.roc_curve(
                gt_labels, pred_probas, labels=["image", "text"]
            )

            wandb.log(
                {
                    "epoch": epoch,
                    "val_loss": val_loss,
                    "val_accuracy": val_accuracy,
                    "ROC": plot,
                },
                step=step,
            )
            logger.info(f"Epoch {epoch}: {val_loss=}, {val_accuracy=}")


def main(data_path: str, output_path: str) -> None:
    config = {
        "query_emb_dim": 896,
        "text_emb_dim": 896,
        "image_emb_dim": 512,
        "towers_hidden_dim": 512,
        "latent_emb_dim": 512,
        "batch_size": 128,
        "n_epochs": 7,
    }
    model = BlenderModel.from_config(config)

    logger.info("Loading data...", end=" ")
    train_val_data = pd.read_csv(data_path)

    # preparing train and val splits
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True)
    train_index, val_index = next(
        splitter.split(
            train_val_data, train_val_data["label"], groups=train_val_data["query"]
        )
    )
    train_data = train_val_data.loc[train_index].reset_index(drop=True)
    val_data = train_val_data.loc[val_index].reset_index(drop=True)
    train_dataset = TripletsDataset(train_data)
    val_dataset = TripletsDataset(val_data)

    logger.info("Done")
    train(config, model, train_dataset, val_dataset)

    model_scripted = torch.jit.script(model)
    model_scripted.save(output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Script for training blender model on query-image-text triplets."
    )
    parser.add_argument(
        "data_path",
        type=str,
        help="Path to the csv file with metadata for blender training.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="blender_model.pt",
        help="Place where the trained model should be saved.",
    )
    args = parser.parse_args()

    main(args.data_path, args.output)
