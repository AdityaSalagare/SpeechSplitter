"""
API Module for the Speech Diarization System

This module provides Flask API endpoints for speech diarization.
"""

from flask import Blueprint

api_bp = Blueprint('api', __name__)

from . import routes
