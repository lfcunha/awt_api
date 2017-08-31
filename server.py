from swt.swt_app import create_app
from gevent.wsgi import WSGIServer
import os


app = create_app()

if os.environ.get('FLASK_DEBUG') is not None and os.environ['FLASK_DEBUG'] == '1':
    print("debug mode")
    app.run(debug=True, host='0.0.0.0', port=5000)
else:
    print('WSGI mode')
    http_server = WSGIServer(('', 5000), app)
    http_server.serve_forever()
