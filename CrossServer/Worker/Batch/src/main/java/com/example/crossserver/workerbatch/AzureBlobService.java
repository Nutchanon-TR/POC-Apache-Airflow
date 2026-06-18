package com.example.crossserver.workerbatch;

import java.nio.file.Path;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import com.azure.storage.blob.BlobContainerClient;
import com.azure.storage.blob.BlobServiceClient;
import com.azure.storage.blob.BlobServiceClientBuilder;

@Service
public class AzureBlobService {

    private static final Logger log = LoggerFactory.getLogger(AzureBlobService.class);

    private final ReverseBatchProperties properties;

    public AzureBlobService(ReverseBatchProperties properties) {
        this.properties = properties;
    }

    /**
     * Uploads a local file to Azure Blob Storage.
     * Does nothing if the connection string is blank (allows running without Azure).
     *
     * @return the full blob URL, or null when upload was skipped
     */
    public String uploadIfConfigured(Path localPath, String blobName) {
        String connStr = properties.getAzureStorageConnectionString();
        if (connStr == null || connStr.isBlank()) {
            log.warn("AZURE_STORAGE_CONNECTION_STRING not configured — skipping blob upload for {}", blobName);
            return null;
        }

        BlobServiceClient client = new BlobServiceClientBuilder()
                .connectionString(connStr)
                .buildClient();

        BlobContainerClient containerClient = client.getBlobContainerClient(properties.getAzureBlobContainer());
        containerClient.getBlobClient(blobName).uploadFromFile(localPath.toString(), true);

        String url = String.format("https://%s.blob.core.windows.net/%s/%s",
                client.getAccountName(), properties.getAzureBlobContainer(), blobName);
        log.info("Uploaded reversed file to Azure Blob: {}", url);
        return url;
    }
}
