from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required
from io import BytesIO

from app.services.file_service import FileService

files_bp = Blueprint('files', __name__)

@files_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    folder = request.form.get('folder', 'documents')
    
    allowed_extensions = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    
    if ext not in allowed_extensions:
        return jsonify({'error': f'File type not allowed. Allowed: {allowed_extensions}'}), 400
    
    content_types = {
        'pdf': 'application/pdf',
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'xls': 'application/vnd.ms-excel',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    }
    
    content_type = content_types.get(ext, 'application/octet-stream')
    
    result = FileService.upload_file(
        file.read(),
        file.filename,
        folder,
        content_type
    )
    
    if result['success']:
        return jsonify({
            'message': 'File uploaded successfully',
            'url': result['url'],
            'blob_name': result['blob_name']
        }), 200
    else:
        return jsonify({'error': result.get('error', 'Upload failed')}), 500

@files_bp.route('/download/<path:blob_name>', methods=['GET'])
@jwt_required()
def download_file(blob_name):
    result = FileService.download_file(blob_name)
    
    if result['success']:
        return send_file(
            BytesIO(result['content']),
            mimetype=result.get('content_type', 'application/octet-stream'),
            as_attachment=True,
            download_name=blob_name.split('/')[-1]
        )
    else:
        return jsonify({'error': result.get('error', 'Download failed')}), 404

@files_bp.route('/delete', methods=['DELETE'])
@jwt_required()
def delete_file():
    data = request.get_json()
    
    if not data.get('blob_name'):
        return jsonify({'error': 'blob_name is required'}), 400
    
    result = FileService.delete_file(data['blob_name'])
    
    if result['success']:
        return jsonify({'message': 'File deleted successfully'}), 200
    else:
        return jsonify({'error': result.get('error', 'Delete failed')}), 500
