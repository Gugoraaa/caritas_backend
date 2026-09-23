from flask import Blueprint, Response, current_app, jsonify

blueprint = Blueprint("donors", __name__)


@blueprint.get("/donors/<int:donor_id>")
def get_donor_detail(donor_id: int) -> Response:
    donor_service = current_app.extensions["donors"]
    return jsonify(donor_service.get_detail(donor_id))

