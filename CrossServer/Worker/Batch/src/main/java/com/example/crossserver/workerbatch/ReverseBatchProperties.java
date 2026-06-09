package com.example.crossserver.workerbatch;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "worker.batch")
public class ReverseBatchProperties {

    private String defaultInputPath = "/tmp/crossserver/in/mock.txt";
    private String defaultOutputPath = "/tmp/crossserver/out/mock_reversed.txt";

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
}
