# Madrid NO₂ Pollution — Personal Time-Series Project

**Transforming exploratory analysis into a production-ready data pipeline**

---

## 🚀 Overview

This repository contains a personal project analyzing and forecasting NO₂ pollution levels in Madrid using 2018 data. It started as an interview exercise but has since evolved into a standalone data engineering and data science pipeline.

---

## 📚 What’s Inside

- **Done**  
  - Exploratory Data Analysis in Jupyter notebooks with NO₂ and temperature data for 2018.  
  - Initial feature exploration and data cleaning routines.

- **To Do**  
  - Develop and validate a 3-day ahead predictive model (SARIMA, XGBoost, LSTM).  
  - Automate end-to-end ingestion from the Madrid Open Data API ([here](https://datos.madrid.es/portal/site/egob/menuitem.c05c1f754a33a9fbe4b2e4b284f1a5a0/?vgnextoid=f3c0f7d512273410VgnVCM2000000c205a0aRCRD&vgnextchannel=374512b9ace9f310VgnVCM100000171f5a0aRCRD&vgnextfmt=default)).
  - Orchestrate pipelines with Apache Airflow.  
  - (Optional) Implement data transformations with dbt.  
  - Refactor notebooks into production-ready Python scripts.  
  - Set up unit/integration tests and CI/CD (GitHub Actions).  
  - Deploy model serving via FastAPI + Docker.  
  - Monitor pipeline health and model performance.

---

## 📐 Architecture

```text
 ┌─────────────┐     ┌───────────────┐     ┌───────────────┐  
 │ Madrid Open │ --> │ Ingest (API)  │ --> │ Staging (S3)  │  
 │ Data/API    │     │ (Airflow DAG) │     └───────────────┘  
 └─────────────┘     └───────────────┘     
                           │  
                           ▼  
                   ┌───────────────────┐  
                   │ Transform (dbt)   │  
                   └───────────────────┘  
                           │  
                           ▼  
                   ┌────────────────────┐  
                   │ Warehouse          │  
                   │ (Redshift/BigQuery)│   
                   └────────────────────┘  
                           │  
                           ▼  
                   ┌───────────────────┐  
                   │ Model Training    │  
                   │ & Serving (API)   │  
                   └───────────────────┘  
                           │  
                           ▼  
                   ┌───────────────────┐  
                   │ Dashboard & Alerts│  
                   └───────────────────┘  
