"""Score the Singapore csv with the production model and compare with the AU test set."""

import argparse

import joblib
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score


def print_scores(name, model, X, y):
    y_prob = model.predict_proba(X)[:, 1]
    y_pred = (y_prob >= 0.5).astype(int)
    print(f"\n=== {name} ===")
    print("rows      :", len(X))
    print(f"rain ratio: {y.mean() * 100:.1f}%")
    print(f"roc_auc   : {roc_auc_score(y, y_prob):.4f}")
    print(f"recall    : {recall_score(y, y_pred):.4f}")
    print(f"precision : {precision_score(y, y_pred):.4f}")
    print(f"f1        : {f1_score(y, y_pred):.4f}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="models/rain_classifier.joblib")
    parser.add_argument("--csv", default="data/raw/weatherSingapore_current.csv")
    parser.add_argument("--split-date", default="2022-01-01")
    args = parser.parse_args()

    model = joblib.load(args.model)

    # singapore file has the target inside the same csv
    df = pd.read_csv(args.csv)
    df = df.dropna(subset=["RainTomorrow"])
    y = (df["RainTomorrow"] == "Yes").astype(int)
    X = df.drop(columns=["Date", "RainTomorrow"])
    print_scores("Singapore", model, X, y)

    # australian test set for comparaison
    X_test = pd.read_csv("data/processed/X_test.csv")
    y_test = pd.read_csv("data/processed/y_test.csv")["RainTomorrow"]
    if y_test.dtype == object:
        y_test = (y_test == "Yes").astype(int)
    print_scores("Australia test set", model, X_test, y_test)

    # split singapore by date, old years to train and new years to test
    is_train = df["Date"] < args.split_date
    X_sg_train, y_sg_train = X[is_train], y[is_train]
    X_sg_test, y_sg_test = X[~is_train], y[~is_train]
    print_scores("AU model on Singapore test years", model, X_sg_test, y_sg_test)

    # same pipeline, but trained again only on singapore
    sg_model = clone(model)
    sg_model.fit(X_sg_train, y_sg_train)
    print_scores("SG model on Singapore test years", sg_model, X_sg_test, y_sg_test)

    # trained again on australia + singapore, like a real retrain with new data
    X_train = pd.read_csv("data/processed/X_train.csv")
    y_train = pd.read_csv("data/processed/y_train.csv")["RainTomorrow"]
    if y_train.dtype == object:
        y_train = (y_train == "Yes").astype(int)
    both_model = clone(model)
    both_model.fit(
        pd.concat([X_train, X_sg_train], ignore_index=True),
        pd.concat([y_train, y_sg_train], ignore_index=True),
    )
    print_scores("AU+SG model on Singapore test years", both_model, X_sg_test, y_sg_test)
    print_scores("AU+SG model on Australia test set", both_model, X_test, y_test)


if __name__ == "__main__":
    main()
