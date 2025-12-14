package main

import (
	"flag"
	"fmt"
	"net"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	pb "github.com/GoogleCloudPlatform/microservices-demo/src/productcatalogservice/genproto"
	healthpb "google.golang.org/grpc/health/grpc_health_v1"

	"cloud.google.com/go/profiler"
	"github.com/sirupsen/logrus"
	"google.golang.org/grpc"

	// Datadog native tracing
	grpctrace "gopkg.in/DataDog/dd-trace-go.v1/contrib/google.golang.org/grpc"
	"gopkg.in/DataDog/dd-trace-go.v1/ddtrace/tracer"
)

var (
	catalogMutex *sync.Mutex
	log          *logrus.Logger
	extraLatency time.Duration

	port = "3550"

	reloadCatalog bool
)

func init() {
	log = logrus.New()
	log.Formatter = &logrus.JSONFormatter{
		FieldMap: logrus.FieldMap{
			logrus.FieldKeyTime:  "timestamp",
			logrus.FieldKeyLevel: "severity",
			logrus.FieldKeyMsg:   "message",
		},
		TimestampFormat: time.RFC3339Nano,
	}
	log.Out = os.Stdout
	catalogMutex = &sync.Mutex{}
}

func main() {
	if os.Getenv("ENABLE_TRACING") == "1" {
		initTracing()
		defer tracer.Stop()
	} else {
		log.Info("Tracing disabled.")
	}

	if os.Getenv("DISABLE_PROFILER") == "" {
		log.Info("Profiling enabled.")
		go initProfiling("productcatalogservice", "1.0.0")
	} else {
		log.Info("Profiling disabled.")
	}

	flag.Parse()

	// set injected latency
	if s := os.Getenv("EXTRA_LATENCY"); s != "" {
		v, err := time.ParseDuration(s)
		if err != nil {
			log.Fatalf("failed to parse EXTRA_LATENCY (%s) as time.Duration: %+v", v, err)
		}
		extraLatency = v
		log.Infof("extra latency enabled (duration: %v)", extraLatency)
	} else {
		extraLatency = time.Duration(0)
	}

	sigs := make(chan os.Signal, 1)
	signal.Notify(sigs, syscall.SIGUSR1, syscall.SIGUSR2)
	go func() {
		for {
			sig := <-sigs
			log.Printf("Received signal: %s", sig)
			if sig == syscall.SIGUSR1 {
				reloadCatalog = true
				log.Infof("Enable catalog reloading")
			} else {
				reloadCatalog = false
				log.Infof("Disable catalog reloading")
			}
		}
	}()

	if os.Getenv("PORT") != "" {
		port = os.Getenv("PORT")
	}
	log.Infof("starting grpc server at :%s", port)
	run(port)
	select {}
}

func run(port string) string {
	listener, err := net.Listen("tcp", fmt.Sprintf(":%s", port))
	if err != nil {
		log.Fatal(err)
	}

	// Create gRPC server with Datadog tracing interceptors
	srv := grpc.NewServer(
		grpc.UnaryInterceptor(grpctrace.UnaryServerInterceptor()),
		grpc.StreamInterceptor(grpctrace.StreamServerInterceptor()))

	svc := &productCatalog{}
	err = loadCatalog(&svc.catalog)
	if err != nil {
		log.Fatalf("could not parse product catalog: %v", err)
	}

	pb.RegisterProductCatalogServiceServer(srv, svc)
	healthpb.RegisterHealthServer(srv, svc)
	go srv.Serve(listener)

	return listener.Addr().String()
}

func initStats() {
	// TODO(drewbr) Implement stats
}

func initTracing() {
	// Get Datadog Agent address from environment
	agentHost := os.Getenv("DD_AGENT_HOST")
	if agentHost == "" {
		agentHost = "datadog-agent"
	}
	agentPort := os.Getenv("DD_TRACE_AGENT_PORT")
	if agentPort == "" {
		agentPort = "8126"
	}

	// Get service configuration
	serviceName := os.Getenv("DD_SERVICE")
	if serviceName == "" {
		serviceName = "productcatalogservice"
	}
	serviceEnv := os.Getenv("DD_ENV")
	if serviceEnv == "" {
		serviceEnv = "hackathon"
	}
	serviceVersion := os.Getenv("DD_VERSION")
	if serviceVersion == "" {
		serviceVersion = "1.0.0"
	}

	// Start the Datadog tracer
	tracer.Start(
		tracer.WithAgentAddr(fmt.Sprintf("%s:%s", agentHost, agentPort)),
		tracer.WithService(serviceName),
		tracer.WithEnv(serviceEnv),
		tracer.WithServiceVersion(serviceVersion),
		tracer.WithAnalytics(true),
	)

	log.Infof("Datadog tracer initialized (agent: %s:%s, service: %s)", agentHost, agentPort, serviceName)
}

func initProfiling(service, version string) {
	for i := 1; i <= 3; i++ {
		if err := profiler.Start(profiler.Config{
			Service:        service,
			ServiceVersion: version,
			// ProjectID must be set if not running on GCP.
			// ProjectID: "my-project",
		}); err != nil {
			log.Warnf("failed to start profiler: %+v", err)
		} else {
			log.Info("started Stackdriver profiler")
			return
		}
		d := time.Second * 10 * time.Duration(i)
		log.Infof("sleeping %v to retry initializing Stackdriver profiler", d)
		time.Sleep(d)
	}
	log.Warn("could not initialize Stackdriver profiler after retrying, giving up")
}
