import requests


def test_health():
    r = requests.get("http://localhost:6000/v2/health")

    assert r.status_code == 200, "Incorrect status code"
    data = r.json()
    assert isinstance(data['version'], str), "Version string not sent by health route"
    assert isinstance(data['min_sdk_version'], str), "Min SDK Version string not sent by health route"
