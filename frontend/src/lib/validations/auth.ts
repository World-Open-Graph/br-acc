import { z } from "zod";

/** Message keys match i18n auth.* keys for validation errors */
const messages = {
  emailRequired: "emailRequired",
  emailInvalid: "emailInvalid",
  passwordRequired: "passwordRequired",
  passwordMinLength: "passwordMinLength",
  confirmPasswordRequired: "confirmPasswordRequired",
  confirmPasswordMismatch: "confirmPasswordMismatch",
  inviteCodeRequired: "inviteCodeRequired",
} as const;

export const loginSchema = z.object({
  email: z
    .string()
    .min(1, { message: messages.emailRequired })
    .email({ message: messages.emailInvalid }),
  password: z
    .string()
    .min(1, { message: messages.passwordRequired })
    .min(8, { message: messages.passwordMinLength }),
});

export const registerSchema = z
  .object({
    email: z
      .string()
      .min(1, { message: messages.emailRequired })
      .email({ message: messages.emailInvalid }),
    password: z
      .string()
      .min(1, { message: messages.passwordRequired })
      .min(8, { message: messages.passwordMinLength }),
    confirmPassword: z
      .string()
      .min(1, { message: messages.confirmPasswordRequired }),
    inviteCode: z
      .string()
      .min(1, { message: messages.inviteCodeRequired })
      .transform((s) => s.trim())
      .refine((s) => s.length > 0, { message: messages.inviteCodeRequired }),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: messages.confirmPasswordMismatch,
    path: ["confirmPassword"],
  });

export type LoginFormValues = z.infer<typeof loginSchema>;
export type RegisterFormValues = z.infer<typeof registerSchema>;

type TFunction = (key: string) => string;

/** Maps Zod/rhf field error message (i18n key) to translated string for auth forms. */
export function getAuthErrorMessage(
  message: string | undefined,
  t: TFunction,
): string {
  if (!message) return "";
  const key = `auth.${message}`;
  const out = t(key);
  return out === key ? key : out;
}
