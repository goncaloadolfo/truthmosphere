import js from '@eslint/js'
import prettierPlugin from 'eslint-plugin-prettier/recommended'
import pluginReact from 'eslint-plugin-react'
import { defineConfig } from 'eslint/config'
import globals from 'globals'
import tseslint from 'typescript-eslint'

export default defineConfig([
  {
    files: ['**/*.{js,mjs,cjs,ts,jsx,tsx}'],
    plugins: { js },
    extends: ['js/recommended'],
    rules: {
      '@typescript-eslint/explicit-module-boundary-types': 'off',
      '@typescript-eslint/no-explicit-any': 'warn', // Warn on usage of 'any'
      'no-console': 'warn',
    },
    ignores: ['**/node_modules/**', '**/dist/**', '**/build/**'],
    settings: {
      react: {
        version: 'detect',
      },
    },
  },
  {
    files: ['**/*.{js,mjs,cjs,ts,jsx,tsx}'],
    languageOptions: { globals: globals.browser },
  },
  tseslint.configs.recommended,
  pluginReact.configs.flat.recommended,
  prettierPlugin,
])
