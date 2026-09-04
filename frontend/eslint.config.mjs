import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    rules: {
      // Allow `any` in limited cases (e.g. Recharts tooltip props)
      "@typescript-eslint/no-explicit-any": "warn",
      // Allow non-null assertions for known-safe patterns (e.g. clamped_from!)
      "@typescript-eslint/no-non-null-assertion": "off",
    },
  },
];

export default eslintConfig;
