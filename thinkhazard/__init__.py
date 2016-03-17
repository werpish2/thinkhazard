import os

from pyramid.config import Configurator
from sqlalchemy import engine_from_config
from papyrus.renderers import GeoJSON

from .settings import (
    load_processing_settings,
    load_local_settings,
    )
from .models import (
    DBSession,
    Base,
    )

from apscheduler.schedulers.background import BackgroundScheduler

# background scheduler to run print jobs asynchronously. by default a thread
# pool with 10 threads is used. to change the number of parallel print jobs,
# see https://apscheduler.readthedocs.org/en/latest/userguide.html#configuring-the-scheduler  # noqa
scheduler = None


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    global scheduler
    scheduler = BackgroundScheduler()
    scheduler.start()

    load_processing_settings(settings)
    load_local_settings(settings)

    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine

    config = Configurator(settings=settings)

    config.include('pyramid_jinja2')
    config.include('papyrus')

    config.add_static_view('static', 'static', cache_max_age=3600,
                           cachebust=True)
    config.add_static_view('lib', settings.get('node_modules'),
                           cache_max_age=86000, cachebust=True)

    if settings['appname'] == 'public':
        add_public_routes(config)

    if settings['appname'] == 'admin':
        config.add_route('admin_index', '/')

        config.add_route('admin_technical_rec', '/technical_rec')
        config.add_route('admin_technical_rec_new', '/technical_rec/new')
        config.add_route('admin_technical_rec_edit',
                         '/technical_rec/{id:\d+}')

        config.add_route('admin_admindiv_hazardsets', '/admindiv_hazardsets')
        config.add_route('admin_admindiv_hazardsets_hazardtype',
                         '/admindiv_hazardsets/{hazardtype:([A-Z]{2})}')

        config.add_route('admin_climate_rec', '/climate_rec')
        config.add_route('admin_climate_rec_hazardtype',
                         '/climate_rec/{hazard_type:([A-Z]{2})}')
        config.add_route('admin_climate_rec_new',
                         '/climate_rec/{hazard_type:([A-Z]{2})}/new')
        config.add_route('admin_climate_rec_edit', '/climate_rec/{id:\d+}')

        config.add_route('admin_hazardcategory',
                         '/{hazard_type:([A-Z]{2})}/{hazard_level:([A-Z]{3})}')

        config.add_route('admin_hazardsets', '/hazardsets')
        config.add_route('admin_hazardset', '/hazardset/{hazardset}')

        add_public_routes(config, prefix='/preview')

    config.add_renderer('geojson', GeoJSON())

    init_pdf_archive_directory(settings.get('pdf_archive_path'))

    scan_ignore = ['thinkhazard.tests']
    if settings['appname'] != 'admin':
        scan_ignore.append('thinkhazard.views.admin')
    config.scan(ignore=scan_ignore)

    return config.make_wsgi_app()


def add_public_routes(config, prefix=''):
    config.add_route('index', prefix or '/')
    config.add_route('about', prefix + '/about')
    config.add_route('faq', prefix + '/faq')

    config.add_route('report', prefix +
                     '/report/{divisioncode:\d+}/{hazardtype:([A-Z]{2})}')
    config.add_route('report_print', prefix +
                     '/report/print/{divisioncode:\d+}/'
                     '{hazardtype:([A-Z]{2})}')
    config.add_route('report_json', prefix +
                     '/report/{divisioncode:\d+}/{hazardtype:([A-Z]{2})}.json')
    config.add_route('create_pdf_report', prefix +
                     '/report/create/{divisioncode:\d+}')
    config.add_route('get_report_status', prefix +
                     '/report/status/{divisioncode:\d+}/{id}.json')
    config.add_route('get_pdf_report', prefix +
                     '/report/{divisioncode:\d+}/{id}.pdf')

    config.add_route('report_overview', prefix + '/report/{divisioncode:\d+}')
    config.add_route('report_overview_slash', prefix +
                     '/report/{divisioncode:\d+}/')
    config.add_route('report_overview_json', prefix +
                     '/report/{divisioncode:\d+}.json')

    config.add_route('administrativedivision', prefix +
                     '/administrativedivision')

    config.add_route('pdf_cover', prefix + '/pdf_cover/{divisioncode:\d+}')
    config.add_route('pdf_about', prefix + '/pdf_about')
    config.add_route('data_source', '/data_source/{hazardset}')


def init_pdf_archive_directory(pdf_archive_path):
    """Make sure that the directory used as report archive exists.
    """
    if not os.path.exists(pdf_archive_path):
        os.makedirs(pdf_archive_path)
