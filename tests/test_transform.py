
import pandas as pd

def test_no_nulls():
    df = pd.read_csv("data/no2_madrid_clean.csv")
    assert df["nitrogen_dioxide"].isnull().sum() == 0
