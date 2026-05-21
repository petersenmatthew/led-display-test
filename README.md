# LED Matrix Prototyper

## Run

From this directory:

```bash
python3 -m http.server 8080
```

Open [http://localhost:8080](http://localhost:8080) in your browser.

Do not open `index.html` from the filesystem; the worker needs a real HTTP URL.

## Web control panel

On the Pi:

```bash
pip install -r web/requirements.txt
python web/app.py            # UI on http://<pi>:5000
sudo python web/mqtt_listener.py   # in another terminal
```

Needs Mosquitto on `localhost:1883`.

## Make Pi script

On laptop:

```bash
python3 scripts/png_to_matrix_script.py assets/my_picture.png my_picture.py
```

On Pi:

```bash
sudo python3 my_picture.py
```

PNG must be 64x32.


