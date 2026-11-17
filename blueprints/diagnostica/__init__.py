"""Diagnóstica blueprint"""
from flask import Blueprint, render_template

diagnostica_bp = Blueprint('diagnostica', __name__, template_folder='templates')

@diagnostica_bp.route('/')
def diagnostica_home():
    # Render diagnostic analysis (placeholder)
    return render_template('diagnostica.html')
