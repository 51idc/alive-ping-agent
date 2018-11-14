#!/usr/bin/env python
import time
import subprocess
import threading
import flask
import multiprocessing.pool

from service import metric_handler
from service import configHelper
from service.logHelper import LogHelper

CONFIG = configHelper.CONFIG
logger = LogHelper().logger


def generate_fping_metrics(host, endpoint, count, dc):
    metrics = []
    COMMAND = "fping -q -c %s %s 2>&1 | tr =, : | cut -d: -f1,3,5 | tr :/ ' '" % (count, host)
    try:
        subp = subprocess.Popen(
            COMMAND,
            shell=True,
            stdout=subprocess.PIPE)
        output = subp.communicate()[0]
    except Exception:
        logger.error("unexpected error while execute cmd : %s" % COMMAND)
        return None

    data = output.split()
    if len(data) == 7:
        host_str, xmt, rcv, loss_rate, _min, _avg, _max = data
    elif len(data) == 4:
        host_str, xmt, rcv, loss_rate = data
        _min = _avg = _max = 0
    else:
        return None

    logger.info('fping result : ' + str(data))

    ms = {
        'alive.ping.alive': 1,
        'alive.ping.status': 1 if _avg > 0 else 0,
        'alive.ping.avg': float(_avg),
        'alive.ping.loss_rate': float(loss_rate.replace('%', '')),
    }
    for key, val in ms.items():
        m = metric_handler.gauge_metric(endpoint, key, val, DC=dc)
        m['step'] = CONFIG['step']
        metrics.append(m)
    return metrics


def alive(step):
    process_count = (multiprocessing.cpu_count() * 2 + 1) if (multiprocessing.cpu_count() * 2 + 1) < 11 else 10
    logger.info("multiprocess count is : %s" % process_count)
    DC = CONFIG["DC"]
    count = CONFIG["ping_count"]
    targets = CONFIG['targets']
    while True:
        pool = multiprocessing.Pool(process_count)
        now = int(time.time())
        metrics = []
        result = []
        for key, val in targets.items():
            result.append(pool.apply_async(generate_fping_metrics, (val, key, count, DC)))
        pool.close()
        pool.join()

        for res in result:
            if res and res.get():
                metrics.extend(res.get())
        metric_handler.push_metrics(metrics)

        dlt = time.time() - now
        logger.info("cycle finished . cost time : %s" % dlt)
        if dlt < step:
            time.sleep(step - dlt)


# flask app
app = flask.Flask(__name__)


@app.route("/add", methods=["POST"])
def add_alive_ping():
    params = flask.request.get_json(force=True, silent=True)
    if not params:
        return flask.jsonify(status="error", msg="json parse error")

    logger.info("add_alive_ping receive data : %s" % str(params))

    host = params.get("host", None)
    endpoint = params.get("endpoint", None)
    if not (host and endpoint):
        return flask.jsonify(status="error", msg="incomplete imfomation")

    targets = CONFIG["targets"]
    if endpoint in targets:
        return flask.jsonify(status="error", msg="duplicated endpoint")

    targets[endpoint] = host
    logger.info("add alive_ping success %s[%s]" % (endpoint, host))
    configHelper.write_config()
    return flask.jsonify(status="ok", msg="ok")


@app.route("/delete", methods=["POST"])
def delete_alive_ping():
    params = flask.request.get_json(force=True, silent=True)
    if not params:
        return flask.jsonify(status="error", msg="json parse error")

    logger.info("delete_alive_ping receive data : %s" % str(params))

    endpoint = params.get("endpoint", None)
    if not endpoint:
        return flask.jsonify(status="error", msg="incomplete information")

    targets = CONFIG["targets"]

    del targets[endpoint]
    logger.info("delete alive_ping success %s" % endpoint)
    configHelper.write_config()
    return flask.jsonify(status="ok", msg="ok")


@app.route("/update", methods=["POST"])
def update_alive_ping():
    params = flask.request.get_json(force=True, silent=True)
    if not params:
        return flask.jsonify(status="error", msg="json parse error")

    logger.info("update_alive_ping receive data : %s" % str(params))

    host = params.get("host", None)
    endpoint = params.get("endpoint", None)
    if not (endpoint and host):
        return flask.jsonify(status="error", msg="incomplete imfomation")

    targets = CONFIG["targets"]
    if not endpoint in targets:
        return flask.jsonify(status="error", msg="no such endpoint")

    targets[endpoint] = host
    logger.info("update alive_ping success %s" % endpoint)
    configHelper.write_config()
    return flask.jsonify(status="ok", msg="ok")


@app.route("/list")
def list_alive_ping():
    return flask.jsonify(CONFIG["targets"])


if __name__ == "__main__":
    t = threading.Thread(target=alive, args=(CONFIG['step'],))
    t.daemon = True
    t.start()

    app.run(host="0.0.0.0",
            port=CONFIG['http'],
            debug=CONFIG['debug'],
            use_reloader=False)
