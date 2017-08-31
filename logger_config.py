LOG_CONFIG = {
     'version': 1,
     'disable_existing_loggers': False,
     'formatters': {
         'standard': {
             'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
         },
     },
     'handlers': {
         'default': {
             'level': 'INFO',
             'class': 'logging.StreamHandler',
         },
         'file': {
             'level': 'WARN',
             'class': "logging.FileHandler",
             'filename': "fse_error.log",
             'formatter': "standard"
             # 'filemode': 'a',
             # 'datefmt' : '%H:%M:%S',
         }
     },
     'loggers': {
         '': {
             'handlers': ['default'],
             'level': 'INFO',
             'propagate': True
         },
         'swt-api': {
             'handlers': ['file', 'default'],
             'level': 'INFO',
             'propagate': False,

         },
     }
 }