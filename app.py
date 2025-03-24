import os
import logging
from flask import Flask, render_template, request, jsonify, send_file, abort
import time

from config import Config
from db.database import Database
from services.scanner import ImageScanner
from services.image_processor import OllamaProcessor
from services.search import ImageSearch

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("image_archiver.log")],
)

logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize services
db = Database()
scanner = ImageScanner()
image_processor = OllamaProcessor()
search_service = ImageSearch(db, image_processor)

# Create database tables if they don't exist
db.initialize_db()


@app.route("/")
def index():
    """Render the main page."""
    return render_template("index.html")


@app.route("/scan", methods=["POST"])
def scan_directory():
    """
    Scan a directory for images and process them.

    Returns:
        JSON response with scan results
    """
    try:
        directory_path = request.form.get("directory")
        if not directory_path:
            return jsonify({"error": "No directory specified"}), 400

        if not os.path.exists(directory_path) or not os.path.isdir(directory_path):
            return jsonify({"error": "Invalid directory path"}), 400

        # Start processing in background
        processed_count = 0
        start_time = time.time()

        for image_info in scanner.scan_directory(directory_path):
            # Check if image is already in database
            existing_image = db.get_image_by_hash(image_info["file_hash"])

            if not existing_image:
                # Insert new image
                db.insert_image(image_info)

                # Process image with llava
                description = image_processor.describe_image(image_info["filepath"])

                # Create embedding
                embedding = image_processor.create_embedding(description)

                # Store description and embedding
                db.insert_description(image_info["file_hash"], description, embedding)

                processed_count += 1

        elapsed_time = time.time() - start_time

        return jsonify(
            {
                "success": True,
                "processed_count": processed_count,
                "elapsed_time": elapsed_time,
            }
        )

    except Exception as e:
        logger.error(f"Error scanning directory: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/search", methods=["GET"])
def search():
    """
    Search for images by SQL or semantic search.

    Returns:
        Rendered template with search results
    """
    try:
        search_type = request.args.get("type", "sql")
        query = request.args.get("query", "")
        page = int(request.args.get("page", 1))
        per_page = Config.SEARCH_RESULTS_PER_PAGE

        if not query:
            return render_template(
                "results.html", images=[], total=0, page=page, per_page=per_page
            )

        results = []

        if search_type == "sql":
            # Sanitize input to prevent SQL injection
            # This is a simple approach, a more robust solution would use prepared statements
            sanitized_query = query.replace("'", "''")

            # Search by SQL query
            sql_query = f"""
                SELECT i.*, d.description
                FROM images i
                LEFT JOIN descriptions d ON i.file_hash = d.image_hash
                WHERE i.filename LIKE '%{sanitized_query}%'
                OR d.description LIKE '%{sanitized_query}%'
                ORDER BY i.filename
                LIMIT {per_page} OFFSET {(page - 1) * per_page}
            """

            images = search_service.search_by_sql(sql_query)
            results = [{"image": image, "similarity": 1.0} for image in images]

            # Get total count for pagination
            count_query = f"""
                SELECT COUNT(*) as total
                FROM images i
                LEFT JOIN descriptions d ON i.file_hash = d.image_hash
                WHERE i.filename LIKE '%{sanitized_query}%'
                OR d.description LIKE '%{sanitized_query}%'
            """

            count_result = db.get_images_by_sql_query(count_query)
            total = count_result[0]["total"] if count_result else 0

        elif search_type == "semantic":
            # Search by semantic similarity
            search_results = search_service.search_by_description(query)

            # Paginate results
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            results = [
                {"image": result.image, "similarity": result.similarity}
                for result in search_results[start_idx:end_idx]
            ]

            total = len(search_results)

        return render_template(
            "results.html",
            results=results,
            query=query,
            search_type=search_type,
            total=total,
            page=page,
            per_page=per_page,
        )

    except Exception as e:
        logger.error(f"Error searching: {e}")
        return render_template(
            "results.html", error=str(e), results=[], total=0, page=1, per_page=per_page
        )


@app.route("/image/<string:file_hash>")
def view_image(file_hash):
    """
    View details of a specific image.

    Args:
        file_hash: Hash of the image file

    Returns:
        Rendered template with image details
    """
    try:
        image_data = db.get_image_by_hash(file_hash)

        if not image_data:
            abort(404)

        # Check if file exists
        if not os.path.exists(image_data["filepath"]):
            return render_template(
                "view.html", error="Image file not found on disk", image=image_data
            )

        return render_template("view.html", image=image_data)

    except Exception as e:
        logger.error(f"Error viewing image: {e}")
        return render_template("view.html", error=str(e))


@app.route("/image_file/<string:file_hash>")
def get_image_file(file_hash):
    """
    Serve an image file.

    Args:
        file_hash: Hash of the image file

    Returns:
        Image file response
    """
    try:
        image_data = db.get_image_by_hash(file_hash)

        if not image_data or not os.path.exists(image_data["filepath"]):
            abort(404)

        return send_file(image_data["filepath"])

    except Exception as e:
        logger.error(f"Error serving image file: {e}")
        abort(500)


@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run(debug=True)
