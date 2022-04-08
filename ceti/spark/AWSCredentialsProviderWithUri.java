import java.io.IOException;
import java.net.URI;
import java.util.Date;
import java.util.logging.Logger;
import java.lang.String;
import org.apache.hadoop.conf.Configurable;
import org.apache.hadoop.conf.Configuration;
import com.amazonaws.auth.AWSCredentials;
import com.amazonaws.auth.AWSCredentialsProvider;
import com.amazonaws.auth.BasicSessionCredentials;
import com.amazonaws.auth.InstanceProfileCredentialsProvider;
import com.amazonaws.auth.PropertiesCredentials;
import com.amazonaws.services.securitytoken.AWSSecurityTokenServiceClient;
import com.amazonaws.services.securitytoken.model.Credentials;
import com.amazonaws.services.securitytoken.model.AssumeRoleRequest;
import com.amazonaws.services.securitytoken.model.AssumeRoleResult;


final class MyAWSCredentialsProviderWithUri implements AWSCredentialsProvider, Configurable {

    private Configuration configuration;
    private AWSCredentials credentials, iamUserCredentials;
    private static final String role_arn =
            "arn:aws:iam::656606567507:role/UpdateS3Role";

    //Specifying the S3 bucket URI for the other account
    private static final String bucket_URI = "s3://projectceti-bucket-021022";

    private URI uri;
    private static InstanceProfileCredentialsProvider creds;
    private static Credentials stsCredentials;

    public MyAWSCredentialsProviderWithUri(URI uri, Configuration conf) {
        this.configuration = conf;
        this.uri = uri;
    }

    @Override
    public AWSCredentials getCredentials() {
        //Returning the credentials to EMRFS to make S3 API calls
        if (uri.toString().startsWith(bucket_URI)) {
            if (stsCredentials == null ||
                    (stsCredentials.getExpiration().getTime() - System.currentTimeMillis() < 60000)) {
                try {
                    //Reading the credentials of the IAM users from Java properties file
                    iamUserCredentials = new PropertiesCredentials
                    (MyAWSCredentialsProviderWithUri.class.getResourceAsStream("Credentials.properties"));
                } catch (IOException e) {
                    e.printStackTrace();
                }
                AWSSecurityTokenServiceClient   stsClient = new
                            AWSSecurityTokenServiceClient(iamUserCredentials);
                //Assuming the role in the other account to obtain temporary credentials
                AssumeRoleRequest assumeRequest = new AssumeRoleRequest()
                .withRoleArn(role_arn)
                .withDurationSeconds(43200)
                .withRoleSessionName("EMRAssumeUpdateS3RoleSession");
                AssumeRoleResult assumeResult = stsClient.assumeRole(assumeRequest);
                stsCredentials = assumeResult.getCredentials();
            }
            BasicSessionCredentials temporaryCredentials =
                    new BasicSessionCredentials(
                            stsCredentials.getAccessKeyId(),
                            stsCredentials.getSecretAccessKey(),
                            stsCredentials.getSessionToken());
            credentials = temporaryCredentials;

        } else {
            //Extracting the credentials from EC2 metadata service
            Boolean refreshCredentialsAsync = true;
            if (creds == null) {
                creds = new InstanceProfileCredentialsProvider
                    (refreshCredentialsAsync);
            }
            credentials = creds.getCredentials();
        }
        return credentials;
    }

    @Override
    public void refresh() {}

    @Override
    public void setConf(Configuration conf) {
    }

    @Override
    public Configuration getConf() {
        return configuration;
    }
}