import { useAuthenticatedImage } from "@/hooks/useAuthenticatedImage";

interface AuthenticatedImageProps extends React.ImgHTMLAttributes<HTMLImageElement> {
  src: string; // ini attachment.url dari API — sekarang sudah berupa endpoint /fkp/.../file
}

export function AuthenticatedImage({ src, alt, ...rest }: AuthenticatedImageProps) {
  const { src: blobSrc, isLoading, error } = useAuthenticatedImage(src);

  if (isLoading) {
    return <div className="animate-pulse bg-muted rounded-md w-full h-full" />;
  }

  if (error || !blobSrc) {
    return (
      <div className="flex items-center justify-center bg-muted text-muted-foreground text-xs rounded-md w-full h-full">
        Gagal memuat gambar
      </div>
    );
  }

  return <img src={blobSrc} alt={alt} {...rest} />;
}