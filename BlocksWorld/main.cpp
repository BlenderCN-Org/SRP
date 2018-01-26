#include <iostream>

#include "opencv2/opencv.hpp"

#include "apriltag.h"
#include "tag36h11.h"
#include "tag36h10.h"
#include "tag36artoolkit.h"
#include "tag25h9.h"
#include "tag25h7.h"
#include "common/getopt.h"
#include "stdlib.h"
#include "libfreenect2.hpp"
#include "common/homography.h"
#include <libfreenect2/libfreenect2.hpp>
#include <libfreenect2/frame_listener_impl.h>
#include <libfreenect2/packet_pipeline.h>


using namespace std;
using namespace cv;


int main(int argc, char *argv[])
{
  VideoCapture capture0(0);
  VideoCapture capture1(1);
  Mat img0, img1, im0gray, im1gray;

  apriltag_detector_t *td = apriltag_detector_create();
  apriltag_detector_add_family(td, tag36h11_create());

  /*  std::string serial = "";
  libfreenect2::Freenect2 freenect2;
  libfreenect2::Freenect2Device *dev = 0;
  libfreenect2::PacketPipeline *pipeline = 0;
  if(!pipeline)
    pipeline = new libfreenect2::OpenGLPacketPipeline();
  if(freenect2.enumerateDevices() == 0)
  {
    std::cout << "no device connected!" << std::endl; 
  }
  else
  {
    serial = freenect2.getDefaultDeviceSerialNumber();
    if(pipeline)
      {
	dev = freenect2.openDevice(serial, pipeline);
      }
    else
    {
      dev = freenect2.openDevice(serial);
    }
  }
  libfreenect2::SyncMultiFrameListener listener(libfreenect2::Frame::Color | libfreenect2::Frame::Ir | libfreenect2::Frame::Depth);
  libfreenect2::FrameMap frames;
  dev->setColorFrameListener(&listener);
  dev->setIrAndDepthFrameListener(&listener);

  int framecount = 0;
  int enable_rgb = 1, enable_depth = 1;
  dev->startStreams(enable_rgb, enable_depth);
  

  cout << "STAGE1" << endl;
  */
  
  while(1)
  {
    //listener.waitForNewFrame(frames, 10*1000); // 10 sconds
    //libfreenect2::Frame *rgb = frames[libfreenect2::Frame::Color];
    //cout << rgb->format << endl;
 	//cout << "Frame params: " << rgb->format << endl; 
    //libfreenect2::Frame *ir = frames[libfreenect2::Frame::Ir];
    //libfreenect2::Frame *depth = frames[libfreenect2::Frame::Depth];
	
    //	Mat image(rgb->height,rgb->width,CV_8UC4,rgb->data); //RGB image, HD resolution
 	
//cv::Mat image_raw;
	//m_cap >> image_raw;

    //	resize(image, image, cv::Size(), 0.5, 0.5);
	//cvtColor(image, image, BGR2RGB);
    //	cvtColor(image, image, COLOR_RGB2GRAY);
	
    capture0 >> img0;
    capture1 >> img1;
    cvtColor(img0, img0, COLOR_BGR2GRAY);
    cvtColor(img1, img1, COLOR_BGR2GRAY);

        // Make an image_u8_t header for the Mat data
        image_u8_t im = { .width = img0.cols,
            .height = img0.rows,
            .stride = img0.cols,
            .buf = img0.data
        };
	image_u8_t im1 = { .width = img1.cols,
            .height = img1.rows,
            .stride = img1.cols,
            .buf = img1.data
        };

	//cout << im.width << " " << im.height << endl;




        zarray_t *detections0 = apriltag_detector_detect(td, &im);
	zarray_t *detections1 = apriltag_detector_detect(td, &im1);
        cout << zarray_size(detections0) << " tags detected" << endl;
	cout << zarray_size(detections1) << " tags detected" << endl;
 
        // Draw detection outlines
        for (int i = 0; i < zarray_size(detections0); i++) {
            apriltag_detection_t *det;
	     //matd_t* H = det->H;
	    //cout << matd_get((det)->H, 0, 0);
	    //cout <<  << " " << TrRot[0][1] << " " << TrRot[0][2] << " " << TrRot[0][3] << endl;
	    // cout << TrRot[1][0] << " " << TrRot[1][1] << " " << TrRot[1][2] << " " << TrRot[1][3] << endl;
	    // cout << TrRot[2][0] << " " << TrRot[2][1] << " " << TrRot[2][2] << " " << TrRot[2][3] << endl;
	    //
            zarray_get(detections0, i, &det);

	    matd_t* TrRot = matd_create(3, 4);
	    TrRot = homography_to_pose(det->H, 600, 600, im.width/2, im.height/2);
	    cout << sqrt(matd_get(TrRot, 0, 3) * matd_get(TrRot, 0, 3) + matd_get(TrRot, 1, 3) * matd_get(TrRot, 1, 3) + matd_get(TrRot, 2, 3) * matd_get(TrRot, 2, 3)); 
            line(img0, Point(det->p[0][0], det->p[0][1]),
                     Point(det->p[1][0], det->p[1][1]),
                     Scalar(0, 0xff, 0), 2);
            line(img0, Point(det->p[0][0], det->p[0][1]),
                     Point(det->p[3][0], det->p[3][1]),
                     Scalar(0, 0, 0xff), 2);
            line(img0, Point(det->p[1][0], det->p[1][1]),
                     Point(det->p[2][0], det->p[2][1]),
                     Scalar(0xff, 0, 0), 2);
            line(img0, Point(det->p[2][0], det->p[2][1]),
                     Point(det->p[3][0], det->p[3][1]),
                     Scalar(0xff, 0, 0), 2);

            stringstream ss;
            ss << det->id;
            String text = ss.str();
            int fontface = FONT_HERSHEY_SCRIPT_SIMPLEX;
            double fontscale = 1.0;
            int baseline;
            Size textsize = getTextSize(text, fontface, fontscale, 2,
                                            &baseline);
            putText(img0, text, Point(det->c[0]-textsize.width/2,
                                       det->c[1]+textsize.height/2),
                    fontface, fontscale, Scalar(0xff, 0x99, 0), 2);
        }
	for (int i = 0; i < zarray_size(detections1); i++) {
            apriltag_detection_t *det;
            zarray_get(detections1, i, &det);
            line(img1, Point(det->p[0][0], det->p[0][1]),
                     Point(det->p[1][0], det->p[1][1]),
                     Scalar(0, 0xff, 0), 2);
            line(img1, Point(det->p[0][0], det->p[0][1]),
                     Point(det->p[3][0], det->p[3][1]),
                     Scalar(0, 0, 0xff), 2);
            line(img1, Point(det->p[1][0], det->p[1][1]),
                     Point(det->p[2][0], det->p[2][1]),
                     Scalar(0xff, 0, 0), 2);
            line(img1, Point(det->p[2][0], det->p[2][1]),
                     Point(det->p[3][0], det->p[3][1]),
                     Scalar(0xff, 0, 0), 2);

            stringstream ss;
            ss << det->id;
            String text = ss.str();
            int fontface = FONT_HERSHEY_SCRIPT_SIMPLEX;
            double fontscale = 1.0;
            int baseline;
            Size textsize = getTextSize(text, fontface, fontscale, 2,
                                            &baseline);
            putText(img1, text, Point(det->c[0]-textsize.width/2,
                                       det->c[1]+textsize.height/2),
                    fontface, fontscale, Scalar(0xff, 0x99, 0), 2);
		    }
	zarray_destroy(detections0);
	zarray_destroy(detections1);


    imshow("0",img0);
    imshow("1", img1);
    //waitKey(1);
    waitKey(50);
    //listener.release(frames);
   
  }
  capture0.release();
  capture1.release();
  //dev->stop();
  //dev->close();
  return 0;
}
