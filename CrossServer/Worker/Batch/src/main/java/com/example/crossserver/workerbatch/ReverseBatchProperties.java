package com.example.crossserver.workerbatch;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "worker.batch")
public class ReverseBatchProperties {

    private String defaultInputPath = "/opt/airflow/shared/ct2-in/mock.txt";
    private String defaultOutputPath = "/opt/airflow/shared/ct2-out/mock_reversed.txt";
    private String azureStorageConnectionString = "";
    private String azureBlobContainer = "crossserver-files";

    public String getDefaultInputPath() {
        return defaultInputPath;
    }

    public void setDefaultInputPath(String defaultInputPath) {
        this.defaultInputPath = defaultInputPath;
    }

    public String getDefaultOutputPath() {
        return defaultOutputPath;
    }

    public void setDefaultOutputPath(String defaultOutputPath) {
        this.defaultOutputPath = defaultOutputPath;
    }

    public String getAzureStorageConnectionString() {
        return azureStorageConnectionString;
    }

    public void setAzureStorageConnectionString(String azureStorageConnectionString) {
        this.azureStorageConnectionString = azureStorageConnectionString;
    }

    public String getAzureBlobContainer() {
        return azureBlobContainer;
    }

    public void setAzureBlobContainer(String azureBlobContainer) {
        this.azureBlobContainer = azureBlobContainer;
    }
}
