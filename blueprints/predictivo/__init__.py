"""Predictivo blueprint"""
from flask import Blueprint, render_template, request
import pandas as pd, os, json, joblib
import plotly.express as px, plotly
from sklearn.ensemble import RandomForestClassifier
from utils import load_config

predictivo_bp = Blueprint('predictivo', __name__, template_folder='templates')

def train_model(df):
    # Simple model: predict 'scene' from a subset of features
    X = df[['year', 'month', 'weekday', 'time_range']]
    # Convert categorical to numeric codes
    for col in X.select_dtypes(include='object').columns:
        X[col] = X[col].astype('category').cat.codes
    y = df['scene']
    y = y.astype('category').cat.codes
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)
    return model, X.columns.tolist()

@predictivo_bp.route('/')
def predictivo_home():
    # Load dataset (cached)
    data_path = os.path.join(os.path.dirname(__file__), '..', 'Data', 'dataset.pkl')
    df = pd.read_pickle(data_path)
    model_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'predictivo_model.pkl')
    if os.path.exists(model_path):
        model, features = joblib.load(model_path)
    else:
        model, features = train_model(df)
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        joblib.dump((model, features), model_path)
    # Show feature importance bar chart
    importances = model.feature_importances_
    fig = px.bar(x=features, y=importances, labels={'x':'Feature','y':'Importancia'}, title='Importancia de variables')
    chart_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return render_template('predictivo.html', chart_json=chart_json)
