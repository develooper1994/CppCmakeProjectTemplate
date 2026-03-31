
#ifndef DUMMY_LIB_EXPORT_H
#define DUMMY_LIB_EXPORT_H

#ifdef DUMMY_LIB_STATIC_DEFINE
#  define DUMMY_LIB_EXPORT
#  define DUMMY_LIB_NO_EXPORT
#else
#  ifndef DUMMY_LIB_EXPORT
#    ifdef dummy_lib_EXPORTS
        /* We are building this library */
#      define DUMMY_LIB_EXPORT 
#    else
        /* We are using this library */
#      define DUMMY_LIB_EXPORT 
#    endif
#  endif

#  ifndef DUMMY_LIB_NO_EXPORT
#    define DUMMY_LIB_NO_EXPORT 
#  endif
#endif

#ifndef DUMMY_LIB_DEPRECATED
#  define DUMMY_LIB_DEPRECATED __attribute__ ((__deprecated__))
#endif

#ifndef DUMMY_LIB_DEPRECATED_EXPORT
#  define DUMMY_LIB_DEPRECATED_EXPORT DUMMY_LIB_EXPORT DUMMY_LIB_DEPRECATED
#endif

#ifndef DUMMY_LIB_DEPRECATED_NO_EXPORT
#  define DUMMY_LIB_DEPRECATED_NO_EXPORT DUMMY_LIB_NO_EXPORT DUMMY_LIB_DEPRECATED
#endif

#if 0 /* DEFINE_NO_DEPRECATED */
#  ifndef DUMMY_LIB_NO_DEPRECATED
#    define DUMMY_LIB_NO_DEPRECATED
#  endif
#endif

#endif /* DUMMY_LIB_EXPORT_H */
