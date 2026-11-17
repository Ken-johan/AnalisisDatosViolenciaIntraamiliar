"""Prescriptivo blueprint"""
from flask import Blueprint, render_template

prescriptivo_bp = Blueprint('prescriptivo', __name__, template_folder='templates')

@prescriptivo_bp.route('/')
def prescriptivo_home():
    # Placeholder for prescriptive analytics
    return render_template('prescriptivo.html')
