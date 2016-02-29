from api.api import app_factory


app = app_factory(__name__, config={
    'TENANT_DSN': 'mysql://test:test@db/common'
})


@app.route('/test')
def test():
    return 'test'


if __name__ == '__main__':
    app.run(
        host=app.config.get('LISTEN_HOST', '0.0.0.0'),
        port=app.config.get('LISTEN_PORT', 5000),
        debug=True,
        use_reloader=True,
        use_debugger=True
    )

