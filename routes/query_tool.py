from flask import Blueprint, render_template, request, redirect, url_for, session, flash

query_tool_bp = Blueprint('query_tool', __name__)

@query_tool_bp.route('/query_tool')
def query_tool():
    return render_template('query_tool.html')