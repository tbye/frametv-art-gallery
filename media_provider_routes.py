from flask import Blueprint, request, jsonify, current_app, Response

media_provider_routes = Blueprint('media_provider', __name__)

# --- Immich/Media Provider Endpoints ---
import asyncio
import logging

logger = logging.getLogger(__name__)

def get_media_provider():
    return getattr(current_app, 'media_provider', None)

def _run_async(coro):
    """Run an async coroutine from a sync Flask view."""
    return asyncio.run(coro)

def _provider_error(exc, action: str):
    logger.exception("Provider error during %s", action)
    return jsonify({"error": f"Provider failed to {action}: {exc}"}), 502

@media_provider_routes.route('/api/provider/albums', methods=['GET'])
def api_provider_albums():
    media_provider = get_media_provider()
    if not media_provider:
        return jsonify({"error": "No external provider configured"}), 404
    try:
        albums = _run_async(media_provider.get_albums())
    except Exception as e:
        return _provider_error(e, "list albums")
    return jsonify({"albums": albums})

@media_provider_routes.route('/api/provider/albums/<album_id>/images', methods=['GET'])
def api_provider_album_images(album_id):
    media_provider = get_media_provider()
    if not media_provider:
        return jsonify({"error": "No external provider configured"}), 404
    try:
        images = _run_async(media_provider.get_album_images(album_id))
    except Exception as e:
        return _provider_error(e, "list album images")
    return jsonify({"images": images})

@media_provider_routes.route('/api/provider/images/<image_id>/stream', methods=['GET'])
def api_provider_stream_image(image_id):
    media_provider = get_media_provider()
    if not media_provider:
        return jsonify({"error": "No external provider configured"}), 404
    size = request.args.get("size", "fullsize")
    app = current_app
    # Simple in-memory cache
    if not hasattr(app, "_provider_image_cache"):
        app._provider_image_cache = {}
    cache_key = f"{image_id}:{size}"
    if cache_key in app._provider_image_cache:
        image_bytes = app._provider_image_cache[cache_key]
    else:
        try:
            image_bytes = _run_async(media_provider.stream_image(image_id=image_id, size=size))
        except Exception as e:
            return _provider_error(e, "stream image")
        if image_bytes:
            app._provider_image_cache[cache_key] = image_bytes
    if not image_bytes:
        return jsonify({"error": "Image not found"}), 404
    return Response(image_bytes, mimetype="image/jpeg")

@media_provider_routes.route('/api/provider/images/<image_id>/metadata', methods=['GET'])
def api_provider_image_metadata(image_id):
    media_provider = get_media_provider()
    if not media_provider:
        return jsonify({"error": "No external provider configured"}), 404
    try:
        metadata = _run_async(media_provider.get_image_metadata(image_id))
    except Exception as e:
        return _provider_error(e, "fetch image metadata")
    return jsonify({"metadata": metadata})
