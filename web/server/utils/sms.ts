export async function sendSms(phone: string, code: string): Promise<boolean> {
  const config = useRuntimeConfig()

  if (!config.smsAccessKey) {
    console.log(`[SMS DEV] Sending code ${code} to ${phone}`)
    return true
  }

  try {
    const response = await $fetch('https://dysmsapi.aliyuncs.com/', {
      method: 'POST',
      query: {
        Action: 'SendSms',
        PhoneNumbers: phone,
        SignName: 'OASIS',
        TemplateCode: 'SMS_TEMPLATE_ID',
        TemplateParam: JSON.stringify({ code }),
        AccessKeyId: config.smsAccessKey,
      },
    })
    return true
  } catch (err) {
    console.error('[SMS] Failed to send:', err)
    return false
  }
}
