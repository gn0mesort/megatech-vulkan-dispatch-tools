doc_env = environment()
doc_env.set('DOXYGEN_PROJECT_NAME', '@0@-tools'.format(meson.project_name()))
doc_env.set('DOXYGEN_PROJECT_NUMBER', meson.project_version())
doc_env.set('DOXYGEN_OUTPUT_DIRECTORY', meson.current_build_dir() / 'documentation')
doc_inputs = [ meson.current_source_dir() / 'megatech', files('README.md')[0].full_path() ]
doc_env.set('DOXYGEN_USE_MDFILE_AS_MAINPAGE', doc_inputs[1])
doc_env.set('DOXYGEN_INPUT', ' '.join(doc_inputs))
doc_env.set('DOXYGEN_HTML_EXTRA_STYLESHEET', extra_css.full_path())
doc_env.set('DOXYGEN_ENABLED_SECTIONS', ' '.join(get_option('enabled_doxygen_sections')))
toolsdoc = custom_target('tools-documentation', output: 'docs', build_always_stale: true,
                         command: [ doxygen, files('Doxyfile') ], env: doc_env, depends: headers)
