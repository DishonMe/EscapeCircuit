module.exports = {
  root: true,
  env: {
    node: true,
    es6: true,
  },
  parserOptions: { ecmaVersion: 'latest', sourceType: 'module' },
  ignorePatterns: [
    'node_modules/*',
    'generators/*',
  ],
  extends: ['eslint:recommended', 'next/core-web-vitals'],
  overrides: [
    {
      files: ['**/*.ts', '**/*.tsx'],
      parser: '@typescript-eslint/parser',
      settings: {
        react: { version: 'detect' },
        'import/resolver': {
          typescript: {},
        },
        tailwindcss: {
          // DOM hook classes used as guided-tour targets and workstation
          // anchors — not Tailwind classes. They're matched by selectors
          // in PageTourLauncher / Joyride and must remain stable strings.
          whitelist: [
            'tour-arsenal-list',
            'tour-arsenal-preview',
            'tour-arsenal-actions',
            'tour-creator-io-config',
            'tour-creator-palette',
            'tour-creator-grid',
            'tour-creator-cost',
            'tour-creator-save',
            'tour-my-puzzles-tabs',
            'tour-my-puzzles-create',
            'tour-my-puzzles-actions',
            'tour-profile-stats',
            'tour-profile-medals',
            'create-puzzle-basic-tab',
            'create-puzzle-solution-tab',
            'create-puzzle-test-cases-tab',
            'create-puzzle-instructions-tab',
            'create-puzzle-custom-pieces-tab',
            'create-puzzle-publish-button',
            'workstation-component-menu',
            'workstation-grid',
            'workstation-check-button',
            'workstation-debugger-button',
            'workstation-instructions-button',
            'workstation-sandbox-toggle',
            'puzzle-filters-button',
            'puzzle-instructions-button',
            'puzzle-sort-dropdown',
            'puzzle-card-action',
            'puzzle-save-button',
            'puzzle-rating-section',
            'dialog-close-button',
            // CSS keyframe / utility class names defined in styled-jsx
            // blocks or globals.css — not Tailwind utilities.
            'workstation-solved-slam',
            'workstation-wire-flow-fast',
            'workstation-wire-snapback',
            'workstation-micro-spark',
            'lock-indicator',
            'ripple-pulse',
          ],
        },
      },
      env: {
        browser: true,
        node: true,
        es6: true,
      },
      extends: [
        'eslint:recommended',
        'plugin:import/errors',
        'plugin:import/warnings',
        'plugin:import/typescript',
        'plugin:@typescript-eslint/recommended',
        'plugin:react/recommended',
        'plugin:react-hooks/recommended',
        'plugin:jsx-a11y/recommended',
        'plugin:prettier/recommended',
        'plugin:tailwindcss/recommended',
      ],
      rules: {
        '@next/next/no-img-element': 'off',
        'import/no-restricted-paths': [
          'error',
          {
            zones: [
              // disables cross-feature imports:
              // eg. src/features/discussions should not import from src/features/comments, etc.
              {
                target: './src/features/auth',
                from: './src/features',
                except: ['./auth'],
              },
              {
                target: './src/features/comments',
                from: './src/features',
                except: ['./comments'],
              },
              {
                target: './src/features/discussions',
                from: './src/features',
                except: ['./discussions'],
              },
              {
                target: './src/features/teams',
                from: './src/features',
                except: ['./teams'],
              },
              {
                target: './src/features/users',
                from: './src/features',
                except: ['./users'],
              },
              // enforce unidirectional codebase:

              // e.g. src/app can import from src/features but not the other way around
              {
                target: './src/features',
                from: './src/app',
              },

              // e.g src/features and src/app can import from these shared modules but not the other way around
              {
                target: [
                  './src/components',
                  './src/hooks',
                  './src/lib',
                  './src/types',
                  './src/utils',
                ],
                from: ['./src/features', './src/app'],
              },
            ],
          },
        ],
        'import/no-cycle': 'error',
        'linebreak-style': ['error', 'unix'],
        'react/prop-types': 'off',
        'import/order': [
          'error',
          {
            groups: [
              'builtin',
              'external',
              'internal',
              'parent',
              'sibling',
              'index',
              'object',
            ],
            'newlines-between': 'always',
            alphabetize: { order: 'asc', caseInsensitive: true },
          },
        ],
        'import/default': 'off',
        'import/no-named-as-default-member': 'off',
        'import/no-named-as-default': 'off',
        'react/react-in-jsx-scope': 'off',
        'jsx-a11y/anchor-is-valid': 'off',
        '@typescript-eslint/no-unused-vars': [
          'error',
          { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
        ],
        '@typescript-eslint/explicit-function-return-type': ['off'],
        '@typescript-eslint/explicit-module-boundary-types': ['off'],
        '@typescript-eslint/no-empty-function': ['off'],
        '@typescript-eslint/no-explicit-any': ['off'],
        'prettier/prettier': ['error', {}, { usePrettierrc: true }],
        // `jsx` / `global` are valid styled-jsx props; the rule doesn't
        // know about styled-jsx so we allow them at the config level
        // rather than scattering inline disables.
        'react/no-unknown-property': ['error', { ignore: ['jsx', 'global'] }],
        // StyledSelect is a custom form control wrapping Radix Select;
        // teach the a11y rule so labels wrapping it pass the check.
        'jsx-a11y/label-has-associated-control': [
          'error',
          { controlComponents: ['StyledSelect'] },
        ],
      },
    },
    {
      files: ['**/*.test.{ts,tsx}', '**/__tests__/**/*.{ts,tsx}'],
      extends: [
        'plugin:testing-library/react',
        'plugin:jest-dom/recommended',
        'plugin:vitest/legacy-recommended',
      ],
    },
    {
      plugins: ['check-file'],
      files: ['src/**/*'],
      rules: {
        'check-file/filename-naming-convention': [
          'error',
          {
            '**/*.{ts,tsx}': 'KEBAB_CASE',
          },
          {
            ignoreMiddleExtensions: true,
          },
        ],
        'check-file/folder-naming-convention': [
          'error',
          {
            '!(src/app)/**/*': 'KEBAB_CASE',
            '!(**/__tests__)/**/*': 'KEBAB_CASE',
          },
        ],
      },
    },
  ],
};
