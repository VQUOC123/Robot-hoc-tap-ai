import pluginVue from 'eslint-plugin-vue'
import tseslint from 'typescript-eslint'
import vueParser from 'vue-eslint-parser'

export default [
  { ignores: ['dist/**', 'node_modules/**'] },
  // Vue files
  {
    files: ['src/**/*.vue'],
    plugins: { vue: pluginVue, '@typescript-eslint': tseslint.plugin },
    languageOptions: {
      parser: vueParser,
      parserOptions: { parser: tseslint.parser },
    },
    rules: {
      ...pluginVue.configs['essential'].rules,
      'vue/multi-word-component-names': 'off',
      'vue/require-default-prop': 'off',
      '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/no-explicit-any': 'warn',
    },
  },
  // TypeScript files
  {
    files: ['src/**/*.ts'],
    plugins: { '@typescript-eslint': tseslint.plugin },
    languageOptions: { parser: tseslint.parser },
    rules: {
      ...tseslint.configs.recommended.at(-1)?.rules,
      '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/no-explicit-any': 'warn',
    },
  },
]
