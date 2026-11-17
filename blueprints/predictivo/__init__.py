"""Predictivo blueprint"""
from flask import Blueprint, render_template

predictivo_bp = Blueprint('predictivo', __name__, template_folder='templates')

@predictivo_bp.route('/')
def predictivo_home():
    # Placeholder for predictive analytics
    return render_template('predictivo.html')
