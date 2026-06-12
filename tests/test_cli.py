import json

from madrid_pollution.cli import main


def test_status_command_reports_project_paths(capsys) -> None:
    assert main(["status"]) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["version"] == "0.1.0"
    assert output["data_years"] == [2018, 2025]
