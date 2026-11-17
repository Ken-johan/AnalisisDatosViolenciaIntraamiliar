"""Descriptivo blueprint"""
from flask import Blueprint, render_template

descriptivo_bp = Blueprint('descriptivo', __name__, template_folder='templates')

@descriptivo_bp.route('/')
def descriptivo_home():
    # Render the descriptive dashboard (previously index.html)
    return render_template('descriptivo.html')
"