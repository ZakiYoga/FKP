// utils/attachmentUrl.ts
export function getAttachmentFileUrl(fkpId: string, attachmentId: string): string {
  return `${import.meta.env.VITE_API_BASE_URL}/fkp/${fkpId}/attachments/${attachmentId}/file`;
}