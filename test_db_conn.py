from sqlalchemy import create_engine, text
engine = create_engine('postgresql+psycopg2://postgres:postgrespassword@localhost:5432/engineering_intelligence_test', connect_args={'connect_timeout': 5})
try:
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1'))
        print('Connection OK:', result.fetchone())
        result = conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'"))
        print('Vector extension:', result.fetchone())
except Exception as e:
    print('Error:', e)