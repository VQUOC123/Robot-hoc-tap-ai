import { z } from 'zod'
import { toTypedSchema } from '@vee-validate/zod'

export const providerSchema = z.object({
  name: z.string().min(1, 'Tên không được trống').max(100),
  base_url: z.string().url('URL không hợp lệ'),
  api_key: z.string().min(10, 'API key phải có ít nhất 10 ký tự'),
  model: z.string().min(1, 'Model không được trống'),
  timeout_sec: z.coerce
    .number()
    .int()
    .min(5, 'Tối thiểu 5 giây')
    .max(120, 'Tối đa 120 giây')
    .default(30),
  is_default: z.boolean().default(false),
})

export const providerVeeSchema = toTypedSchema(providerSchema)
export type ProviderFormValues = z.infer<typeof providerSchema>
